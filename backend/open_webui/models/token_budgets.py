import os
import time
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, Integer, String, Text
from sqlalchemy.orm import Session

from open_webui.internal.db import Base, get_db_context

DEFAULT_SIGNUP_TOKEN_BUDGET = int(os.environ.get("DEFAULT_SIGNUP_TOKEN_BUDGET", "2000"))
DEFAULT_PLUS_TOKEN_BUDGET = int(os.environ.get("DEFAULT_PLUS_TOKEN_BUDGET", "3000"))
DEFAULT_PRO_TOKEN_BUDGET = int(
    os.environ.get("DEFAULT_PRO_TOKEN_BUDGET", os.environ.get("DEFAULT_PRO_TOEKN_BUDGET", "4000"))
)
DEFAULT_ENTERPRISE_TOKEN_BUDGET = int(os.environ.get("DEFAULT_ENTERPRISE_TOKEN_BUDGET", "5000"))


class TokenBudget(Base):
    __tablename__ = "token_budget"

    id = Column(Text, primary_key=True, unique=True)
    user_id = Column(Text, unique=True, index=True, nullable=False)
    window_type = Column(String(32), nullable=False, default="monthly")
    timezone = Column(String(64), nullable=True)
    limit_tokens = Column(Integer, nullable=False, default=0)
    enabled = Column(Boolean, nullable=False, default=True)
    created_by = Column(Text, nullable=False)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class TokenBudgetModel(BaseModel):
    id: str
    user_id: str
    window_type: str = "monthly"
    timezone: Optional[str] = None
    limit_tokens: int
    enabled: bool = True
    created_by: str
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class TokenBudgetTable:
    def _plan_limit_tokens(self, plan_id: Optional[str]) -> Optional[int]:
        if not plan_id:
            return None

        key = str(plan_id).strip().lower()
        if key == "plus":
            return DEFAULT_PLUS_TOKEN_BUDGET
        if key == "pro":
            return DEFAULT_PRO_TOKEN_BUDGET
        if key == "enterprise":
            return DEFAULT_ENTERPRISE_TOKEN_BUDGET
        return None

    def ensure_default_signup_budget(
        self,
        *,
        user_id: str,
        created_by: str,
        db: Optional[Session] = None,
    ) -> TokenBudgetModel:
        with get_db_context(db) as db:
            record = db.query(TokenBudget).filter_by(user_id=user_id).first()
            if record is not None:
                return TokenBudgetModel.model_validate(record)

            now = int(time.time())
            record = TokenBudget(
                id=str(uuid.uuid4()),
                user_id=user_id,
                window_type="monthly",
                timezone=None,
                limit_tokens=DEFAULT_SIGNUP_TOKEN_BUDGET,
                enabled=True,
                created_by=created_by,
                created_at=now,
                updated_at=now,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return TokenBudgetModel.model_validate(record)

    def apply_plan_budget(
        self,
        *,
        user_id: str,
        plan_id: Optional[str],
        created_by: str,
        db: Optional[Session] = None,
    ) -> Optional[TokenBudgetModel]:
        limit_tokens = self._plan_limit_tokens(plan_id)
        if limit_tokens is None:
            return None
        return self.upsert_budget(
            user_id=user_id,
            created_by=created_by,
            limit_tokens=limit_tokens,
            enabled=True,
            timezone=None,
            window_type="monthly",
            db=db,
        )

    def upsert_budget(
        self,
        *,
        user_id: str,
        created_by: str,
        limit_tokens: int,
        enabled: bool = True,
        timezone: Optional[str] = None,
        window_type: str = "monthly",
        db: Optional[Session] = None,
    ) -> TokenBudgetModel:
        with get_db_context(db) as db:
            now = int(time.time())
            record = db.query(TokenBudget).filter_by(user_id=user_id).first()
            if record is None:
                record = TokenBudget(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    window_type=window_type,
                    timezone=timezone,
                    limit_tokens=limit_tokens,
                    enabled=enabled,
                    created_by=created_by,
                    created_at=now,
                    updated_at=now,
                )
                db.add(record)
            else:
                record.window_type = window_type
                record.timezone = timezone
                record.limit_tokens = limit_tokens
                record.enabled = enabled
                record.updated_at = now

            db.commit()
            db.refresh(record)
            return TokenBudgetModel.model_validate(record)

    def get_by_user_id(
        self, user_id: str, db: Optional[Session] = None
    ) -> Optional[TokenBudgetModel]:
        with get_db_context(db) as db:
            record = db.query(TokenBudget).filter_by(user_id=user_id).first()
            return TokenBudgetModel.model_validate(record) if record else None


TokenBudgets = TokenBudgetTable()

