from datetime import datetime, time
from typing import Optional

import pytz
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from open_webui.internal.db import get_session
from open_webui.models.token_usage import TokenUsageEvent, TokenWindowAggregate
from open_webui.utils.auth import get_verified_user
from open_webui.utils.token_budget import TokenBudgetService, get_month_window

router = APIRouter()


class TokenUsageSummaryResponse(BaseModel):
    window_start: int
    window_end: int
    limit_tokens: int
    used_tokens: int
    reserved_tokens: int
    remaining_tokens: int
    used_percent: float
    timezone: Optional[str] = None


class TokenUsageSeriesPoint(BaseModel):
    date: str
    tokens: int
    top_model: Optional[str] = None


class TokenUsageModelBreakdownRow(BaseModel):
    model: str
    tokens: int
    share: int


class TokenUsageActivityRow(BaseModel):
    id: str
    timestamp: int
    model: Optional[str] = None
    type: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    conversation_id: Optional[str] = None


class TokenUsageActivityList(BaseModel):
    data: list[TokenUsageActivityRow]
    page: int
    total: int


class TokenUsageActivityDetail(TokenUsageActivityRow):
    metadata: Optional[dict] = None


def _resolve_timezone(user_tz: Optional[str]) -> pytz.BaseTzInfo:
    if user_tz:
        try:
            return pytz.timezone(user_tz)
        except Exception:
            return pytz.UTC
    return pytz.UTC


def _parse_date(date_str: str, tz: pytz.BaseTzInfo, end_of_day: bool) -> int:
    date_val = datetime.strptime(date_str, "%Y-%m-%d").date()
    dt = datetime.combine(date_val, time.max if end_of_day else time.min)
    localized = tz.localize(dt)
    return int(localized.astimezone(pytz.UTC).timestamp())


def _get_window(
    *,
    user_tz: Optional[str],
    start: Optional[str],
    end: Optional[str],
) -> tuple[int, int, Optional[str]]:
    tz = _resolve_timezone(user_tz)
    if start or end:
        start_epoch = (
            _parse_date(start, tz, False) if start else int(datetime.now(tz).timestamp())
        )
        end_epoch = (
            _parse_date(end, tz, True) if end else int(datetime.now(tz).timestamp())
        )
        if end_epoch < start_epoch:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date range",
            )
        return start_epoch, end_epoch, tz.zone

    window = get_month_window(tz_name=tz.zone)
    return window.window_start, window.reset_at, tz.zone


@router.get("/token-usage/summary", response_model=TokenUsageSummaryResponse)
async def get_token_usage_summary(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    timezone: Optional[str] = Query(None),
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    status = TokenBudgetService.get_status(user_id=user.id, db=db)
    user_tz = timezone or (status.timezone if status else None)
    window_start, window_end, tz_name = _get_window(
        user_tz=user_tz, start=start, end=end
    )

    used_tokens = 0
    reserved_tokens = 0

    # Prefer window aggregate when using the default monthly window
    if start is None and end is None:
        aggregate = (
            db.query(TokenWindowAggregate)
            .filter(TokenWindowAggregate.user_id == user.id)
            .filter(TokenWindowAggregate.window_start == window_start)
            .first()
        )
        if aggregate is not None:
            used_tokens = int(getattr(aggregate, "used_tokens", 0) or 0)
            reserved_tokens = int(getattr(aggregate, "reserved_tokens", 0) or 0)

    if used_tokens == 0 and reserved_tokens == 0:
        events = (
            db.query(TokenUsageEvent)
            .filter(TokenUsageEvent.user_id == user.id)
            .filter(TokenUsageEvent.created_at >= window_start)
            .filter(TokenUsageEvent.created_at <= window_end)
            .all()
        )
        used_tokens = sum(
            int(e.total_tokens or 0) for e in events if e.status != "reserved"
        )
        reserved_tokens = sum(
            int(e.total_tokens or 0) for e in events if e.status == "reserved"
        )

    limit_tokens = int(status.limit_tokens) if status else 0
    remaining_tokens = (
        max(limit_tokens - used_tokens - reserved_tokens, 0) if limit_tokens else 0
    )
    used_percent = (
        (used_tokens / limit_tokens) * 100 if limit_tokens > 0 else 0.0
    )

    return TokenUsageSummaryResponse(
        window_start=window_start,
        window_end=window_end,
        limit_tokens=limit_tokens,
        used_tokens=used_tokens,
        reserved_tokens=reserved_tokens,
        remaining_tokens=remaining_tokens,
        used_percent=used_percent,
        timezone=tz_name,
    )


@router.get("/token-usage/series", response_model=list[TokenUsageSeriesPoint])
async def get_token_usage_series(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    timezone: Optional[str] = Query(None),
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    status = TokenBudgetService.get_status(user_id=user.id, db=db)
    user_tz = timezone or (status.timezone if status else None)
    window_start, window_end, tz_name = _get_window(
        user_tz=user_tz, start=start, end=end
    )
    tz = _resolve_timezone(user_tz)

    events = (
        db.query(TokenUsageEvent)
        .filter(TokenUsageEvent.user_id == user.id)
        .filter(TokenUsageEvent.created_at >= window_start)
        .filter(TokenUsageEvent.created_at <= window_end)
        .filter(TokenUsageEvent.status != "reserved")
        .all()
    )

    day_map: dict[str, dict] = {}
    for event in events:
        date_key = datetime.fromtimestamp(event.created_at, tz=tz).strftime("%Y-%m-%d")
        if date_key not in day_map:
            day_map[date_key] = {"tokens": 0, "models": {}}
        day_map[date_key]["tokens"] += int(event.total_tokens or 0)
        if event.model_id:
            day_map[date_key]["models"].setdefault(event.model_id, 0)
            day_map[date_key]["models"][event.model_id] += int(event.total_tokens or 0)

    points: list[TokenUsageSeriesPoint] = []
    for date_key in sorted(day_map.keys()):
        models = day_map[date_key]["models"]
        top_model = max(models, key=models.get) if models else None
        points.append(
            TokenUsageSeriesPoint(
                date=date_key,
                tokens=day_map[date_key]["tokens"],
                top_model=top_model,
            )
        )
    return points


@router.get("/token-usage/models", response_model=list[TokenUsageModelBreakdownRow])
async def get_token_usage_by_model(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    timezone: Optional[str] = Query(None),
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    status = TokenBudgetService.get_status(user_id=user.id, db=db)
    user_tz = timezone or (status.timezone if status else None)
    window_start, window_end, _ = _get_window(
        user_tz=user_tz, start=start, end=end
    )

    events = (
        db.query(TokenUsageEvent)
        .filter(TokenUsageEvent.user_id == user.id)
        .filter(TokenUsageEvent.created_at >= window_start)
        .filter(TokenUsageEvent.created_at <= window_end)
        .filter(TokenUsageEvent.status != "reserved")
        .all()
    )

    totals: dict[str, int] = {}
    for event in events:
        model_key = event.model_id or "unknown"
        totals[model_key] = totals.get(model_key, 0) + int(event.total_tokens or 0)

    total_tokens = sum(totals.values()) or 1
    rows = [
        TokenUsageModelBreakdownRow(
            model=model,
            tokens=tokens,
            share=int(round((tokens / total_tokens) * 100)),
        )
        for model, tokens in sorted(totals.items(), key=lambda item: item[1], reverse=True)
    ]
    return rows


@router.get("/token-usage/activity", response_model=TokenUsageActivityList)
async def get_token_usage_activity(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    timezone: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    status = TokenBudgetService.get_status(user_id=user.id, db=db)
    user_tz = timezone or (status.timezone if status else None)
    window_start, window_end, _ = _get_window(
        user_tz=user_tz, start=start, end=end
    )

    query = (
        db.query(TokenUsageEvent)
        .filter(TokenUsageEvent.user_id == user.id)
        .filter(TokenUsageEvent.created_at >= window_start)
        .filter(TokenUsageEvent.created_at <= window_end)
        .filter(TokenUsageEvent.status != "reserved")
    )
    if model:
        query = query.filter(TokenUsageEvent.model_id == model)
    if type:
        query = query.filter(TokenUsageEvent.route == type)

    total = query.count()
    offset = (page - 1) * limit
    rows = (
        query.order_by(TokenUsageEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    def _map_row(event: TokenUsageEvent) -> TokenUsageActivityRow:
        metadata = getattr(event, "metadata_", None) or {}
        return TokenUsageActivityRow(
            id=event.id,
            timestamp=int(event.created_at),
            model=event.model_id,
            type=event.route or "chat",
            input_tokens=int(event.prompt_tokens or 0),
            output_tokens=int(event.completion_tokens or 0),
            total_tokens=int(event.total_tokens or 0),
            conversation_id=metadata.get("chat_id") or metadata.get("conversation_id"),
        )

    return TokenUsageActivityList(
        data=[_map_row(row) for row in rows],
        page=page,
        total=total,
    )


@router.get("/token-usage/activity/{activity_id}", response_model=TokenUsageActivityDetail)
async def get_token_usage_activity_detail(
    activity_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    event = (
        db.query(TokenUsageEvent)
        .filter(TokenUsageEvent.user_id == user.id)
        .filter(TokenUsageEvent.id == activity_id)
        .first()
    )
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    metadata = getattr(event, "metadata_", None) or {}
    safe_metadata = {
        key: value
        for key, value in metadata.items()
        if key in {"chat_id", "conversation_id", "note", "source"}
    }
    return TokenUsageActivityDetail(
        id=event.id,
        timestamp=int(event.created_at),
        model=event.model_id,
        type=event.route or "chat",
        input_tokens=int(event.prompt_tokens or 0),
        output_tokens=int(event.completion_tokens or 0),
        total_tokens=int(event.total_tokens or 0),
        conversation_id=metadata.get("chat_id") or metadata.get("conversation_id"),
        metadata=safe_metadata,
    )
