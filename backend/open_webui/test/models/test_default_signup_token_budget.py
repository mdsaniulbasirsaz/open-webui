import os

os.environ.setdefault("WEBUI_AUTH", "False")
os.environ.setdefault("WEBUI_SECRET_KEY", "test-secret")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from open_webui.models.auths import Auths, Auth
from open_webui.models.users import User
from open_webui.models.token_budgets import (
    TokenBudget,
    TokenBudgets,
    DEFAULT_SIGNUP_TOKEN_BUDGET,
)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Auth.__table__.create(bind=engine)
    User.__table__.create(bind=engine)
    TokenBudget.__table__.create(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_signup_creates_default_token_budget(db_session):
    user = Auths.insert_new_auth(
        "u1@example.com",
        "hashed",
        "User One",
        role="user",
        db=db_session,
    )
    assert user is not None

    budget = db_session.query(TokenBudget).filter_by(user_id=user.id).first()
    assert budget is not None
    assert budget.limit_tokens == DEFAULT_SIGNUP_TOKEN_BUDGET
    assert budget.enabled is True


def test_signup_does_not_overwrite_existing_budget(monkeypatch, db_session):
    fixed_id = "00000000-0000-0000-0000-000000000000"

    class _FixedUUID:
        def __str__(self):
            return fixed_id

    monkeypatch.setattr("open_webui.models.auths.uuid.uuid4", lambda: _FixedUUID())

    db_session.add(
        TokenBudget(
            id="b1",
            user_id=fixed_id,
            window_type="monthly",
            timezone=None,
            limit_tokens=9999,
            enabled=True,
            created_by="seed",
            created_at=1,
            updated_at=1,
        )
    )
    db_session.commit()

    user = Auths.insert_new_auth(
        "u2@example.com",
        "hashed",
        "User Two",
        role="user",
        db=db_session,
    )
    assert user is not None
    assert user.id == fixed_id

    budget = db_session.query(TokenBudget).filter_by(user_id=fixed_id).first()
    assert budget is not None
    assert budget.limit_tokens == 9999


def test_completed_payment_plan_updates_budget(monkeypatch, db_session):
    monkeypatch.setenv("DEFAULT_PLUS_TOKEN_BUDGET", "3000")
    monkeypatch.setenv("DEFAULT_PRO_TOEKN_BUDGET", "4000")
    monkeypatch.setenv("DEFAULT_ENTERPRISE_TOKEN_BUDGET", "5000")

    user = Auths.insert_new_auth(
        "u3@example.com",
        "hashed",
        "User Three",
        role="user",
        db=db_session,
    )
    assert user is not None

    before = db_session.query(TokenBudget).filter_by(user_id=user.id).first()
    assert before is not None
    assert before.limit_tokens == DEFAULT_SIGNUP_TOKEN_BUDGET

    updated = TokenBudgets.apply_plan_budget(
        user_id=user.id,
        plan_id="plus",
        created_by=user.id,
        db=db_session,
    )
    assert updated is not None

    after = db_session.query(TokenBudget).filter_by(user_id=user.id).first()
    assert after is not None
    assert after.limit_tokens == 3000
