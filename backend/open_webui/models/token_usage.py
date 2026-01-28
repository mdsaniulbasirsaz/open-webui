import time
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    BigInteger,
    Column,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from open_webui.internal.db import Base, get_db_context


class TokenUsageEvent(Base):
    __tablename__ = "token_usage_event"

    id = Column(Text, primary_key=True, unique=True)
    request_id = Column(Text, unique=True, index=True, nullable=False)
    user_id = Column(Text, index=True, nullable=False)
    model_id = Column(Text, nullable=True)
    provider = Column(String(32), nullable=True)
    route = Column(String(128), nullable=True)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    status = Column(String(16), nullable=False, default="success")
    created_at = Column(BigInteger, nullable=False, index=True)
    metadata_ = Column("metadata", JSON, nullable=True)


class TokenWindowAggregate(Base):
    __tablename__ = "token_window_aggregate"

    id = Column(Text, primary_key=True, unique=True)
    user_id = Column(Text, index=True, nullable=False)
    window_start = Column(BigInteger, nullable=False)
    limit_tokens_snapshot = Column(Integer, nullable=False)
    used_tokens = Column(Integer, nullable=False, default=0)
    reserved_tokens = Column(Integer, nullable=False, default=0)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "window_start", name="token_window_user_start_uq"),
    )


class TokenUsageEventModel(BaseModel):
    id: str
    request_id: str
    user_id: str
    model_id: Optional[str] = None
    provider: Optional[str] = None
    route: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    status: str = "success"
    created_at: int
    metadata: Optional[dict] = Field(default=None, validation_alias="metadata_")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TokenWindowAggregateModel(BaseModel):
    id: str
    user_id: str
    window_start: int
    limit_tokens_snapshot: int
    used_tokens: int = 0
    reserved_tokens: int = 0
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class TokenUsageTable:
    def insert_event(
        self,
        *,
        request_id: str,
        user_id: str,
        status: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        model_id: Optional[str] = None,
        provider: Optional[str] = None,
        route: Optional[str] = None,
        metadata: Optional[dict] = None,
        created_at: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> TokenUsageEventModel:
        with get_db_context(db) as db:
            existing = (
                db.query(TokenUsageEvent).filter_by(request_id=request_id).first()
            )
            if existing is not None:
                return TokenUsageEventModel.model_validate(existing)

            now = int(time.time()) if created_at is None else int(created_at)
            record = TokenUsageEvent(
                id=str(uuid.uuid4()),
                request_id=request_id,
                user_id=user_id,
                model_id=model_id,
                provider=provider,
                route=route,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                status=status,
                created_at=now,
                metadata_=metadata,
            )
            db.add(record)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                existing = (
                    db.query(TokenUsageEvent).filter_by(request_id=request_id).first()
                )
                if existing is not None:
                    return TokenUsageEventModel.model_validate(existing)
                raise

            db.refresh(record)
            return TokenUsageEventModel.model_validate(record)


class TokenWindowAggregatesTable:
    def upsert_window(
        self,
        *,
        user_id: str,
        window_start: int,
        limit_tokens_snapshot: int,
        db: Optional[Session] = None,
    ) -> TokenWindowAggregateModel:
        with get_db_context(db) as db:
            record = (
                db.query(TokenWindowAggregate)
                .filter_by(user_id=user_id, window_start=window_start)
                .first()
            )
            now = int(time.time())
            if record is None:
                record = TokenWindowAggregate(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    window_start=window_start,
                    limit_tokens_snapshot=limit_tokens_snapshot,
                    used_tokens=0,
                    reserved_tokens=0,
                    updated_at=now,
                )
                db.add(record)
            else:
                record.limit_tokens_snapshot = limit_tokens_snapshot
                record.updated_at = now

            db.commit()
            db.refresh(record)
            return TokenWindowAggregateModel.model_validate(record)


TokenUsage = TokenUsageTable()
TokenWindowAggregates = TokenWindowAggregatesTable()
