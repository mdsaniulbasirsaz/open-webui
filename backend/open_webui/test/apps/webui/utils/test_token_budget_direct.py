from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

import open_webui.utils.chat as chat


def _make_request() -> Request:
    scope = {
        "type": "http",
        "asgi": {"spec_version": "2.3", "version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/chat/completions",
        "raw_path": b"/api/v1/chat/completions",
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "state": {},
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_direct_path_enforces_token_budget(monkeypatch):
    request = _make_request()
    request.state.direct = True
    request.state.model = {"id": "m1", "owned_by": "openai"}

    user = SimpleNamespace(id="u1", role="user")

    called = {"reserve": 0, "finalize": 0}
    seen = {"request_id": None}

    def fake_reserve(**_kwargs):
        called["reserve"] += 1
        seen["request_id"] = _kwargs.get("request_id")
        return SimpleNamespace(remaining_tokens=0)

    def fake_finalize(**_kwargs):
        called["finalize"] += 1

    async def fake_event_call(_payload):
        return {"usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}}

    monkeypatch.setattr(chat.TokenBudgetService, "reserve", staticmethod(fake_reserve))
    monkeypatch.setattr(chat.TokenBudgetService, "finalize", staticmethod(fake_finalize))
    monkeypatch.setattr(chat, "get_event_call", lambda _metadata: fake_event_call)

    res = await chat.generate_chat_completion(
        request,
        form_data={
            "model": "m1",
            "metadata": {"user_id": "u1", "session_id": "s1", "request_id": "client-controlled"},
            "stream": False,
        },
        user=user,
    )

    assert called["reserve"] == 1
    assert called["finalize"] == 1
    assert seen["request_id"] is not None
    assert seen["request_id"] != "client-controlled"
    assert isinstance(res, dict)


@pytest.mark.asyncio
async def test_direct_path_blocks_when_exceeded(monkeypatch):
    request = _make_request()
    request.state.direct = True
    request.state.model = {"id": "m1", "owned_by": "openai"}

    user = SimpleNamespace(id="u1", role="user")

    def fake_reserve(**_kwargs):
        raise chat.TokenBudgetExceededError(
            limit=100,
            used=100,
            remaining=0,
            window="monthly",
            reset_at=1738368000,
        )

    monkeypatch.setattr(chat.TokenBudgetService, "reserve", staticmethod(fake_reserve))
    monkeypatch.setattr(chat, "get_event_call", lambda _metadata: None)

    with pytest.raises(HTTPException) as exc:
        await chat.generate_chat_completion(
            request,
            form_data={
                "model": "m1",
                "metadata": {"user_id": "u1", "session_id": "s1"},
                "stream": False,
            },
            user=user,
        )

    assert exc.value.status_code == 429
    assert exc.value.detail["code"] == "TOKEN_BUDGET_EXCEEDED"
