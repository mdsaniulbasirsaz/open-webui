import os
from types import SimpleNamespace

os.environ.setdefault("WEBUI_AUTH", "False")
os.environ.setdefault("WEBUI_SECRET_KEY", "test-secret")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from open_webui.internal.db import get_session
from open_webui.routers import payments
from open_webui.models.payments import PaymentTransaction
from open_webui.utils.auth import get_current_user


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    PaymentTransaction.__table__.create(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    app = FastAPI()
    app.state.config = SimpleNamespace(WEBUI_NAME="Open WebUI")
    app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])

    def _override_get_session():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_session] = _override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_session, None)
    app.dependency_overrides.pop(get_current_user, None)


def _insert_transaction(db_session, *, transaction_id: str, user_id: str):
    db_session.add(
        PaymentTransaction(
            id=transaction_id,
            user_id=user_id,
            plan_id="pro",
            amount=10.0,
            currency="USD",
            status="paid",
            payment_id="p1",
            trx_id="t1",
            merchant_invoice_number="INV-001",
            raw_response={},
            created_at=1700000000,
            updated_at=1700000001,
        )
    )
    db_session.commit()


def test_download_invoice_pdf_owner_only_ok(client, db_session):
    _insert_transaction(db_session, transaction_id="tx1", user_id="u1")

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="u1", name="John Doe", email="john.doe@openwebui.com", role="user"
    )

    res = client.get("/api/v1/payments/invoices/tx1.pdf")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/pdf")
    assert "attachment;" in res.headers.get("content-disposition", "")
    assert res.content[:4] == b"%PDF"


def test_download_invoice_pdf_other_user_forbidden(client, db_session):
    _insert_transaction(db_session, transaction_id="tx2", user_id="u1")

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="u2", name="Jane Doe", email="jane.doe@openwebui.com", role="user"
    )

    res = client.get("/api/v1/payments/invoices/tx2.pdf")
    assert res.status_code == 403
