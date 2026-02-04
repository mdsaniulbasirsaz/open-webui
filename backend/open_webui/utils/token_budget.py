import time
import uuid
import os
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pytz
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from open_webui.internal.db import get_db_context
from open_webui.models.token_budgets import TokenBudget, TokenBudgetModel
from open_webui.models.token_usage import TokenUsageEvent, TokenWindowAggregate

log = logging.getLogger(__name__)

DEFAULT_STALE_RESERVATION_TTL_SECONDS = int(
    os.environ.get("TOKEN_BUDGET_STALE_RESERVATION_TTL_SECONDS", "")
)
DEFAULT_STALE_RESERVATION_SWEEP_LIMIT = int(
    os.environ.get("TOKEN_BUDGET_STALE_RESERVATION_SWEEP_LIMIT", "")
)


class TokenBudgetExceededError(Exception):
    def __init__(
        self,
        *,
        limit: int,
        used: int,
        remaining: int,
        window: str,
        reset_at: int,
    ):
        super().__init__("Monthly token limit exceeded.")
        self.limit = limit
        self.used = used
        self.remaining = remaining
        self.window = window
        self.reset_at = reset_at

    def to_error_payload(self) -> dict:
        return {
            "code": "TOKEN_BUDGET_EXCEEDED",
            "message": "Monthly token limit exceeded.",
            "limit": self.limit,
            "used": self.used,
            "remaining": self.remaining,
            "window": self.window,
            "reset_at": self.reset_at,
        }


class TokenBudgetStatusModel(BaseModel):
    user_id: str
    enabled: bool
    window_type: str
    timezone: Optional[str] = None
    window_start: int
    reset_at: int
    limit_tokens: int
    used_tokens: int
    reserved_tokens: int
    remaining_tokens: int

    model_config = ConfigDict(from_attributes=True)


@dataclass(frozen=True)
class TokenWindow:
    window_start: int
    reset_at: int


def _get_timezone(tz_name: Optional[str]) -> pytz.BaseTzInfo:
    if tz_name:
        try:
            return pytz.timezone(tz_name)
        except Exception:
            pass
    return pytz.UTC


def get_month_window(*, now_epoch: Optional[int] = None, tz_name: Optional[str] = None) -> TokenWindow:
    now_epoch = int(time.time()) if now_epoch is None else int(now_epoch)
    tz = _get_timezone(tz_name)

    now_local = datetime.fromtimestamp(now_epoch, tz=tz)
    month_start_local = tz.localize(
        datetime(now_local.year, now_local.month, 1, 0, 0, 0), is_dst=None
    )
    if now_local.month == 12:
        next_month_local = tz.localize(datetime(now_local.year + 1, 1, 1, 0, 0, 0), is_dst=None)
    else:
        next_month_local = tz.localize(
            datetime(now_local.year, now_local.month + 1, 1, 0, 0, 0), is_dst=None
        )

    window_start = int(month_start_local.astimezone(pytz.UTC).timestamp())
    reset_at = int(next_month_local.astimezone(pytz.UTC).timestamp())
    return TokenWindow(window_start=window_start, reset_at=reset_at)


class TokenBudgetService:
    @staticmethod
    def get_budget(user_id: str, db: Optional[Session] = None) -> Optional[TokenBudgetModel]:
        with get_db_context(db) as db:
            record = db.query(TokenBudget).filter_by(user_id=user_id).first()
            return TokenBudgetModel.model_validate(record) if record else None

    @staticmethod
    def get_status(
        *,
        user_id: str,
        now_epoch: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> Optional[TokenBudgetStatusModel]:
        with get_db_context(db) as db:
            budget = db.query(TokenBudget).filter_by(user_id=user_id).first()
            if not budget:
                return None

            window = get_month_window(now_epoch=now_epoch, tz_name=budget.timezone)
            agg = TokenBudgetService._get_or_create_window_aggregate(
                db=db,
                user_id=user_id,
                window_start=window.window_start,
                limit_tokens_snapshot=int(getattr(budget, "limit_tokens", 0) or 0),
            )
            used = int(getattr(agg, "used_tokens", 0) or 0)
            reserved = int(getattr(agg, "reserved_tokens", 0) or 0)
            remaining = max(int(budget.limit_tokens) - used - reserved, 0)

            return TokenBudgetStatusModel(
                user_id=user_id,
                enabled=bool(budget.enabled),
                window_type=budget.window_type,
                timezone=budget.timezone,
                window_start=window.window_start,
                reset_at=window.reset_at,
                limit_tokens=int(budget.limit_tokens),
                used_tokens=used,
                reserved_tokens=reserved,
                remaining_tokens=remaining,
            )

    @staticmethod
    def _get_or_create_window_aggregate(
        *,
        db: Session,
        user_id: str,
        window_start: int,
        limit_tokens_snapshot: int,
    ) -> TokenWindowAggregate:
        record = (
            db.query(TokenWindowAggregate)
            .filter_by(user_id=user_id, window_start=window_start)
            .first()
        )
        if record is not None:
            if int(record.limit_tokens_snapshot) != int(limit_tokens_snapshot):
                record.limit_tokens_snapshot = int(limit_tokens_snapshot)
                record.updated_at = int(time.time())
                db.commit()
            return record

        record = TokenWindowAggregate(
            id=str(uuid.uuid4()),
            user_id=user_id,
            window_start=window_start,
            limit_tokens_snapshot=int(limit_tokens_snapshot),
            used_tokens=0,
            reserved_tokens=0,
            updated_at=int(time.time()),
        )
        db.add(record)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            record = (
                db.query(TokenWindowAggregate)
                .filter_by(user_id=user_id, window_start=window_start)
                .first()
            )
            if record is None:
                raise
        return record

    @staticmethod
    def reserve(
        *,
        user_id: str,
        request_id: str,
        estimate_tokens: int,
        prompt_tokens_estimate: int = 0,
        completion_tokens_estimate: int = 0,
        model_id: Optional[str] = None,
        provider: Optional[str] = None,
        route: Optional[str] = None,
        metadata: Optional[dict] = None,
        now_epoch: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> Optional[TokenBudgetStatusModel]:
        """
        Returns status (including remaining) when enforced; returns None when no enabled budget is configured.
        Raises TokenBudgetExceededError when the reservation cannot be made.
        """
        estimate_tokens = max(int(estimate_tokens or 0), 0)
        prompt_tokens_estimate = max(int(prompt_tokens_estimate or 0), 0)
        completion_tokens_estimate = max(int(completion_tokens_estimate or 0), 0)
        if estimate_tokens <= 0 and (prompt_tokens_estimate > 0 or completion_tokens_estimate > 0):
            estimate_tokens = prompt_tokens_estimate + completion_tokens_estimate
        with get_db_context(db) as db:
            budget = db.query(TokenBudget).filter_by(user_id=user_id).first()
            if not budget or not budget.enabled:
                return None
            limit_tokens = int(getattr(budget, "limit_tokens", 0) or 0)

            window = get_month_window(now_epoch=now_epoch, tz_name=budget.timezone)
            agg = TokenBudgetService._get_or_create_window_aggregate(
                db=db,
                user_id=user_id,
                window_start=window.window_start,
                limit_tokens_snapshot=limit_tokens,
            )

            # Idempotency: if the request already exists, don't double-reserve.
            existing_event = db.query(TokenUsageEvent).filter_by(request_id=request_id).first()
            if existing_event is not None:
                used = int(agg.used_tokens or 0)
                reserved = int(agg.reserved_tokens or 0)
                remaining = max(int(budget.limit_tokens) - used - reserved, 0)
                return TokenBudgetStatusModel(
                    user_id=user_id,
                    enabled=bool(budget.enabled),
                    window_type=budget.window_type,
                    timezone=budget.timezone,
                    window_start=window.window_start,
                    reset_at=window.reset_at,
                    limit_tokens=int(budget.limit_tokens),
                    used_tokens=used,
                    reserved_tokens=reserved,
                    remaining_tokens=remaining,
                )

            # Atomic reservation: update only if remaining allows.
            now = int(time.time())
            # limit_tokens <= 0 means "no limit" (still track usage, but don't enforce a ceiling).
            query = db.query(TokenWindowAggregate).filter(
                and_(
                    TokenWindowAggregate.user_id == user_id,
                    TokenWindowAggregate.window_start == window.window_start,
                )
            )
            if limit_tokens > 0:
                query = query.filter(
                    (TokenWindowAggregate.used_tokens + TokenWindowAggregate.reserved_tokens + estimate_tokens)
                    <= TokenWindowAggregate.limit_tokens_snapshot
                )
            updated = query.update(
                {
                    TokenWindowAggregate.reserved_tokens: TokenWindowAggregate.reserved_tokens
                    + estimate_tokens,
                    TokenWindowAggregate.updated_at: now,
                },
                synchronize_session=False,
            )

            if updated != 1:
                db.rollback()
                db.refresh(agg)
                used = int(agg.used_tokens or 0)
                reserved = int(agg.reserved_tokens or 0)
                remaining = max(limit_tokens - used - reserved, 0)
                raise TokenBudgetExceededError(
                    limit=limit_tokens,
                    used=used,
                    remaining=remaining,
                    window=budget.window_type,
                    reset_at=window.reset_at,
                )

            # Write reservation marker (event).
            event = TokenUsageEvent(
                id=str(uuid.uuid4()),
                request_id=request_id,
                user_id=user_id,
                model_id=model_id,
                provider=provider,
                route=route,
                prompt_tokens=prompt_tokens_estimate,
                completion_tokens=completion_tokens_estimate,
                total_tokens=estimate_tokens,
                status="reserved",
                created_at=now,
                metadata_=metadata,
            )
            db.add(event)

            try:
                db.commit()
            except IntegrityError:
                # If another worker inserted the event, roll back and undo our reservation.
                db.rollback()
                TokenBudgetService._undo_reservation(
                    db=db,
                    user_id=user_id,
                    window_start=window.window_start,
                    estimate_tokens=estimate_tokens,
                )
                raise

            agg = db.query(TokenWindowAggregate).filter_by(id=agg.id).first()
            used = int(getattr(agg, "used_tokens", 0) or 0)
            reserved = int(getattr(agg, "reserved_tokens", 0) or 0)
            remaining = max(limit_tokens - used - reserved, 0)
            return TokenBudgetStatusModel(
                user_id=user_id,
                enabled=bool(budget.enabled),
                window_type=budget.window_type,
                timezone=budget.timezone,
                window_start=window.window_start,
                reset_at=window.reset_at,
                limit_tokens=limit_tokens,
                used_tokens=used,
                reserved_tokens=reserved,
                remaining_tokens=remaining,
            )

    @staticmethod
    def _undo_reservation(*, db: Session, user_id: str, window_start: int, estimate_tokens: int) -> None:
        estimate_tokens = max(int(estimate_tokens or 0), 0)
        now = int(time.time())
        # Ensure the aggregate exists so we don't silently lose updates.
        agg = (
            db.query(TokenWindowAggregate)
            .filter_by(user_id=user_id, window_start=window_start)
            .first()
        )
        if agg is None:
            agg = TokenWindowAggregate(
                id=str(uuid.uuid4()),
                user_id=user_id,
                window_start=window_start,
                limit_tokens_snapshot=0,
                used_tokens=0,
                reserved_tokens=0,
                updated_at=now,
            )
            db.add(agg)
            db.commit()
        db.query(TokenWindowAggregate).filter(
            and_(
                TokenWindowAggregate.user_id == user_id,
                TokenWindowAggregate.window_start == window_start,
            )
        ).update(
            {
                TokenWindowAggregate.reserved_tokens: TokenWindowAggregate.reserved_tokens
                - estimate_tokens,
                TokenWindowAggregate.updated_at: now,
            },
            synchronize_session=False,
        )
        db.commit()

    @staticmethod
    def finalize(
        *,
        request_id: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: Optional[int] = None,
        status: str = "success",
        metadata: Optional[dict] = None,
        db: Optional[Session] = None,
    ) -> None:
        """
        Converts an existing reservation (status=reserved) into final usage.
        No-op if the event does not exist (caller can decide whether that's acceptable).
        """
        prompt_tokens = max(int(prompt_tokens or 0), 0)
        completion_tokens = max(int(completion_tokens or 0), 0)
        if total_tokens is None:
            total_tokens = prompt_tokens + completion_tokens
        total_tokens = max(int(total_tokens or 0), 0)

        with get_db_context(db) as db:
            event = db.query(TokenUsageEvent).filter_by(request_id=request_id).first()
            if event is None:
                return
            # Idempotency: only convert a reservation once.
            if getattr(event, "status", None) != "reserved":
                return

            estimate_tokens = max(int(event.total_tokens or 0), 0)
            user_id = event.user_id

            # Compute window from event timestamp (reservation time).
            budget = db.query(TokenBudget).filter_by(user_id=user_id).first()
            tz_name = getattr(budget, "timezone", None) if budget else None
            window = get_month_window(now_epoch=int(event.created_at), tz_name=tz_name)
            TokenBudgetService._get_or_create_window_aggregate(
                db=db,
                user_id=user_id,
                window_start=window.window_start,
                limit_tokens_snapshot=int(getattr(budget, "limit_tokens", 0) or 0)
                if budget is not None
                else 0,
            )

            # Update event to final usage.
            event.prompt_tokens = prompt_tokens
            event.completion_tokens = completion_tokens
            event.total_tokens = total_tokens
            event.status = status
            if metadata is not None:
                event.metadata_ = metadata

            # Adjust aggregates: reserved -= estimate, used += total.
            now = int(time.time())
            db.query(TokenWindowAggregate).filter(
                and_(
                    TokenWindowAggregate.user_id == user_id,
                    TokenWindowAggregate.window_start == window.window_start,
                )
            ).update(
                {
                    TokenWindowAggregate.reserved_tokens: TokenWindowAggregate.reserved_tokens
                    - estimate_tokens,
                    TokenWindowAggregate.used_tokens: TokenWindowAggregate.used_tokens + total_tokens,
                    TokenWindowAggregate.updated_at: now,
                },
                synchronize_session=False,
            )
            db.commit()

    @staticmethod
    def release(
        *,
        request_id: str,
        status: str = "canceled",
        db: Optional[Session] = None,
    ) -> None:
        """
        Releases an existing reservation (if any) and marks the event as canceled/error.
        """
        with get_db_context(db) as db:
            event = db.query(TokenUsageEvent).filter_by(request_id=request_id).first()
            if event is None:
                return
            # Idempotency: only undo a reservation once.
            if getattr(event, "status", None) != "reserved":
                return

            estimate_tokens = max(int(event.total_tokens or 0), 0)
            user_id = event.user_id

            budget = db.query(TokenBudget).filter_by(user_id=user_id).first()
            tz_name = getattr(budget, "timezone", None) if budget else None
            window = get_month_window(now_epoch=int(event.created_at), tz_name=tz_name)
            TokenBudgetService._get_or_create_window_aggregate(
                db=db,
                user_id=user_id,
                window_start=window.window_start,
                limit_tokens_snapshot=int(getattr(budget, "limit_tokens", 0) or 0)
                if budget is not None
                else 0,
            )

            now = int(time.time())
            db.query(TokenWindowAggregate).filter(
                and_(
                    TokenWindowAggregate.user_id == user_id,
                    TokenWindowAggregate.window_start == window.window_start,
                )
            ).update(
                {
                    TokenWindowAggregate.reserved_tokens: TokenWindowAggregate.reserved_tokens
                    - estimate_tokens,
                    TokenWindowAggregate.updated_at: now,
                },
                synchronize_session=False,
            )

            event.status = status
            db.commit()

    @staticmethod
    def sweep_stale_reservations(
        *,
        max_age_seconds: int = DEFAULT_STALE_RESERVATION_TTL_SECONDS,
        limit: int = DEFAULT_STALE_RESERVATION_SWEEP_LIMIT,
        db: Optional[Session] = None,
    ) -> int:
        """
        Converts stale reservations (status=reserved) into finalized usage to prevent
        permanently-inflated reserved_tokens when workers crash or streams never finalize.

        This charges the reservation estimate (event.total_tokens) as used tokens and marks
        the event as canceled with metadata indicating it was swept.
        """
        max_age_seconds = max(int(max_age_seconds or 0), 0)
        limit = max(int(limit or 0), 1)
        now = int(time.time())
        cutoff = now - max_age_seconds

        with get_db_context(db) as db:
            query = (
                db.query(TokenUsageEvent)
                .filter(TokenUsageEvent.status == "reserved")
                .filter(TokenUsageEvent.created_at < cutoff)
                .order_by(TokenUsageEvent.created_at.asc())
                .limit(limit)
            )
            events = list(query.all() or [])
            swept = 0

            for event in events:
                request_id = getattr(event, "request_id", None)
                user_id = getattr(event, "user_id", None)
                if not request_id or not user_id:
                    continue

                estimate_total = max(int(getattr(event, "total_tokens", 0) or 0), 0)
                prompt_est = max(int(getattr(event, "prompt_tokens", 0) or 0), 0)
                completion_est = max(int(getattr(event, "completion_tokens", 0) or 0), 0)
                if completion_est <= 0 and estimate_total > 0 and prompt_est > 0:
                    completion_est = max(estimate_total - prompt_est, 0)
                if estimate_total <= 0:
                    estimate_total = prompt_est + completion_est

                budget = db.query(TokenBudget).filter_by(user_id=user_id).first()
                tz_name = getattr(budget, "timezone", None) if budget else None
                window = get_month_window(now_epoch=int(event.created_at), tz_name=tz_name)
                TokenBudgetService._get_or_create_window_aggregate(
                    db=db,
                    user_id=user_id,
                    window_start=window.window_start,
                    limit_tokens_snapshot=int(getattr(budget, "limit_tokens", 0) or 0)
                    if budget is not None
                    else 0,
                )

                existing_meta = getattr(event, "metadata_", None) or {}
                merged_meta = (
                    {**existing_meta}
                    if isinstance(existing_meta, dict)
                    else {"previous_metadata": existing_meta}
                )
                merged_meta.update(
                    {
                        "estimated": True,
                        "swept_stale_reservation": True,
                        "stale_after_seconds": max_age_seconds,
                    }
                )

                updated = (
                    db.query(TokenUsageEvent)
                    .filter(TokenUsageEvent.request_id == request_id)
                    .filter(TokenUsageEvent.status == "reserved")
                    .update(
                        {
                            TokenUsageEvent.prompt_tokens: prompt_est,
                            TokenUsageEvent.completion_tokens: completion_est,
                            TokenUsageEvent.total_tokens: estimate_total,
                            TokenUsageEvent.status: "canceled",
                            TokenUsageEvent.metadata_: merged_meta,
                        },
                        synchronize_session=False,
                    )
                )
                if updated != 1:
                    continue

                db.query(TokenWindowAggregate).filter(
                    and_(
                        TokenWindowAggregate.user_id == user_id,
                        TokenWindowAggregate.window_start == window.window_start,
                    )
                ).update(
                    {
                        TokenWindowAggregate.reserved_tokens: TokenWindowAggregate.reserved_tokens
                        - estimate_total,
                        TokenWindowAggregate.used_tokens: TokenWindowAggregate.used_tokens
                        + estimate_total,
                        TokenWindowAggregate.updated_at: now,
                    },
                    synchronize_session=False,
                )
                swept += 1

            if swept:
                db.commit()
                log.info(f"Swept {swept} stale token reservations (cutoff={cutoff}).")
            return int(swept)
