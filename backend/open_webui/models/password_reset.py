import logging
import time
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String
from sqlalchemy.orm import Session

from open_webui.internal.db import Base, get_db_context

log = logging.getLogger(__name__)


class PasswordResetRequest(Base):
    __tablename__ = "password_reset_request"

    id = Column(String, primary_key=True, unique=True)
    user_id = Column(String, index=True)
    email = Column(String, index=True)
    token_hash = Column(String, index=True)
    expires_at = Column(BigInteger)
    used_at = Column(BigInteger, nullable=True)
    created_at = Column(BigInteger)
    last_sent_at = Column(BigInteger)
    revoked_at = Column(BigInteger, nullable=True)


class PasswordResetRequestModel(BaseModel):
    id: str
    user_id: Optional[str]
    email: str
    token_hash: str
    expires_at: int
    used_at: Optional[int] = None
    created_at: int
    last_sent_at: int
    revoked_at: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class PasswordResetRequestTable:
    def upsert_for_user(
        self,
        user_id: str,
        email: str,
        token_hash: str,
        expires_at: int,
        last_sent_at: int,
        revoked_at: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> PasswordResetRequestModel:
        with get_db_context(db) as db_session:
            record = db_session.query(PasswordResetRequest).filter_by(email=email).first()
            if record:
                record.token_hash = token_hash
                record.expires_at = expires_at
                record.last_sent_at = last_sent_at
                record.used_at = None
                record.revoked_at = revoked_at
                db_session.commit()
                db_session.refresh(record)
                return PasswordResetRequestModel.model_validate(record)

            record = PasswordResetRequest(
                id=str(uuid.uuid4()),
                user_id=user_id,
                email=email,
                token_hash=token_hash,
                expires_at=expires_at,
                used_at=None,
                created_at=int(time.time()),
                last_sent_at=last_sent_at,
                revoked_at=revoked_at,
            )
            db_session.add(record)
            db_session.commit()
            db_session.refresh(record)
            return PasswordResetRequestModel.model_validate(record)

    def get_by_token_hash(
        self, token_hash: str, db: Optional[Session] = None
    ) -> Optional[PasswordResetRequestModel]:
        try:
            with get_db_context(db) as db_session:
                record = (
                    db_session.query(PasswordResetRequest)
                    .filter_by(token_hash=token_hash)
                    .first()
                )
                return PasswordResetRequestModel.model_validate(record) if record else None
        except Exception:
            return None

    def mark_as_used(
        self, token_hash: str, used_at: Optional[int] = None, db: Optional[Session] = None
    ) -> bool:
        with get_db_context(db) as db_session:
            record = (
                db_session.query(PasswordResetRequest)
                .filter_by(token_hash=token_hash)
                .first()
            )
            if not record:
                return False
            record.used_at = used_at or int(time.time())
            db_session.commit()
            return True


PasswordResetRequests = PasswordResetRequestTable()
