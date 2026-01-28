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
from open_webui.routers import token_budgets
from open_webui.models.token_budgets import TokenBudget
from open_webui.models.token_usage import TokenUsageEvent, TokenWindowAggregate
from open_webui.utils.auth import get_current_user


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    TokenBudget.__table__.create(bind=engine)
    TokenUsageEvent.__table__.create(bind=engine)
    TokenWindowAggregate.__table__.create(bind=engine)
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
    app.include_router(token_budgets.router, prefix="/api/v1", tags=["token-budgets"])

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


def test_admin_can_set_budget_and_read_status(client):
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="admin1", role="admin"
    )

    res = client.put(
        "/api/v1/admin/token-budgets/users/u1",
        json={"limit_tokens": 1000, "enabled": True, "timezone": "UTC"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["user_id"] == "u1"
    assert body["limit_tokens"] == 1000
    assert body["enabled"] is True

    status = client.get("/api/v1/admin/token-budgets/users/u1/status")
    assert status.status_code == 200
    status_body = status.json()
    assert status_body["user_id"] == "u1"
    assert status_body["limit_tokens"] == 1000
    assert status_body["enabled"] is True


def test_non_admin_forbidden(client):
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="u2", role="user"
    )

    res = client.put(
        "/api/v1/admin/token-budgets/users/u1",
        json={"limit_tokens": 1000, "enabled": True},
    )
    assert res.status_code == 401

