import logging
import time
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import Session

from open_webui.internal.db import Base, get_db_context

log = logging.getLogger(__name__)


class EmailVerification(Base):
    __tablename__ = "email_verification"

    id = Column(String, primary_key=True, unique=True)
    user_id = Column(String, index=True)
    email = Column(String, index=True)
    code_hash = Column(String)
    attempts_remaining = Column(Integer)
    expires_at = Column(Integer)
    last_sent_at = Column(Integer)
    intended_role = Column(String)
    created_at = Column(Integer)
    verified_at = Column(Integer, nullable=True)
    disable_signup_after_verify = Column(Boolean, default=False)


class EmailVerificationModel(BaseModel):
    id: str
    user_id: str
    email: str
    code_hash: str
    attempts_remaining: int
    expires_at: int
    last_sent_at: int
    intended_role: str
    created_at: int
    verified_at: Optional[int] = None
    disable_signup_after_verify: bool = False

    model_config = ConfigDict(from_attributes=True)


class EmailVerificationTable:
    def get_by_email(
        self, email: str, db: Optional[Session] = None
    ) -> Optional[EmailVerificationModel]:
        try:
            with get_db_context(db) as db:
                record = db.query(EmailVerification).filter_by(email=email).first()
                return EmailVerificationModel.model_validate(record) if record else None
        except Exception:
            return None

    def upsert_for_user(
        self,
        user_id: str,
        email: str,
        code_hash: str,
        expires_at: int,
        attempts_remaining: int,
        intended_role: str,
        last_sent_at: int,
        disable_signup_after_verify: bool,
        db: Optional[Session] = None,
    ) -> EmailVerificationModel:
        with get_db_context(db) as db:
            record = db.query(EmailVerification).filter_by(email=email).first()
            if record:
                record.code_hash = code_hash
                record.expires_at = expires_at
                record.attempts_remaining = attempts_remaining
                record.last_sent_at = last_sent_at
                record.intended_role = intended_role
                record.disable_signup_after_verify = disable_signup_after_verify
                db.commit()
                db.refresh(record)
                return EmailVerificationModel.model_validate(record)

            record = EmailVerification(
                id=str(uuid.uuid4()),
                user_id=user_id,
                email=email,
                code_hash=code_hash,
                attempts_remaining=attempts_remaining,
                expires_at=expires_at,
                last_sent_at=last_sent_at,
                intended_role=intended_role,
                created_at=int(time.time()),
                verified_at=None,
                disable_signup_after_verify=disable_signup_after_verify,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return EmailVerificationModel.model_validate(record)

    def decrement_attempts(
        self, email: str, db: Optional[Session] = None
    ) -> Optional[int]:
        with get_db_context(db) as db:
            record = db.query(EmailVerification).filter_by(email=email).first()
            if not record:
                return None
            record.attempts_remaining = max(0, (record.attempts_remaining or 0) - 1)
            db.commit()
            return record.attempts_remaining

    def delete_by_email(self, email: str, db: Optional[Session] = None) -> bool:
        with get_db_context(db) as db:
            result = db.query(EmailVerification).filter_by(email=email).delete()
            db.commit()
            return result > 0


EmailVerifications = EmailVerificationTable()
