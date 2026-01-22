import time
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, JSON, Numeric, String, Text
from sqlalchemy.orm import Session

from open_webui.internal.db import Base, get_db_context


class PaymentTransaction(Base):
    __tablename__ = "payment_transaction"

    id = Column(Text, primary_key=True, unique=True)
    user_id = Column(Text, index=True)
    plan_id = Column(Text, nullable=True)
    amount = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(8), nullable=True)
    status = Column(String(32), nullable=True)
    payment_id = Column(Text, index=True, nullable=True)
    trx_id = Column(Text, nullable=True)
    merchant_invoice_number = Column(Text, index=True, nullable=True)
    raw_response = Column(JSON, nullable=True)
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class PaymentEvent(Base):
    __tablename__ = "payment_event"

    id = Column(Text, primary_key=True, unique=True)
    payment_id = Column(Text, index=True, nullable=True)
    event_type = Column(String(64), nullable=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(BigInteger)


class PaymentTransactionModel(BaseModel):
    id: str
    user_id: str
    plan_id: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    payment_id: Optional[str] = None
    trx_id: Optional[str] = None
    merchant_invoice_number: Optional[str] = None
    raw_response: Optional[dict] = None
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class PaymentEventModel(BaseModel):
    id: str
    payment_id: Optional[str] = None
    event_type: Optional[str] = None
    payload: Optional[dict] = None
    created_at: int

    model_config = ConfigDict(from_attributes=True)


class PaymentTransactionTable:
    def create_transaction(
        self,
        user_id: str,
        plan_id: Optional[str],
        amount: Optional[float],
        currency: Optional[str],
        status: str,
        payment_id: Optional[str],
        merchant_invoice_number: Optional[str],
        raw_response: Optional[dict],
        db: Optional[Session] = None,
    ) -> PaymentTransactionModel:
        with get_db_context(db) as db:
            now = int(time.time())
            txn = PaymentTransactionModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                plan_id=plan_id,
                amount=amount,
                currency=currency,
                status=status,
                payment_id=payment_id,
                trx_id=None,
                merchant_invoice_number=merchant_invoice_number,
                raw_response=raw_response,
                created_at=now,
                updated_at=now,
            )
            result = PaymentTransaction(**txn.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return PaymentTransactionModel.model_validate(result)

    def get_by_payment_id(
        self, payment_id: str, db: Optional[Session] = None
    ) -> Optional[PaymentTransactionModel]:
        with get_db_context(db) as db:
            record = db.query(PaymentTransaction).filter_by(payment_id=payment_id).first()
            return PaymentTransactionModel.model_validate(record) if record else None

    def update_by_payment_id(
        self,
        payment_id: str,
        status: Optional[str] = None,
        trx_id: Optional[str] = None,
        raw_response: Optional[dict] = None,
        db: Optional[Session] = None,
    ) -> Optional[PaymentTransactionModel]:
        with get_db_context(db) as db:
            record = db.query(PaymentTransaction).filter_by(payment_id=payment_id).first()
            if not record:
                return None

            if status is not None:
                record.status = status
            if trx_id is not None:
                record.trx_id = trx_id
            if raw_response is not None:
                record.raw_response = raw_response

            record.updated_at = int(time.time())
            db.commit()
            db.refresh(record)
            return PaymentTransactionModel.model_validate(record)


class PaymentEventTable:
    def record_event(
        self,
        payment_id: Optional[str],
        event_type: Optional[str],
        payload: Optional[dict],
        db: Optional[Session] = None,
    ) -> PaymentEventModel:
        with get_db_context(db) as db:
            event = PaymentEventModel(
                id=str(uuid.uuid4()),
                payment_id=payment_id,
                event_type=event_type,
                payload=payload,
                created_at=int(time.time()),
            )
            result = PaymentEvent(**event.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return PaymentEventModel.model_validate(result)


PaymentTransactions = PaymentTransactionTable()
PaymentEvents = PaymentEventTable()
