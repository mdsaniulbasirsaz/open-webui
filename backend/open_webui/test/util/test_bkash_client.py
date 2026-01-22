import time

from open_webui.utils.bkash_client import BkashClient


class DummyResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("Request failed")


class StubBkashClient(BkashClient):
    def __init__(self):
        super().__init__(
            base_url="",
            app_key="app_key",
            app_secret="app_secret",
            username="user",
            password="pass",
            timeout_seconds=30,
        )
        self.call_count = 0

    def _request(self, *args, **kwargs):
        self.call_count += 1
        return DummyResponse({"id_token": "token-123", "expires_in": 120})


def test_token_cached():
    client = StubBkashClient()
    token_first = client.get_token()
    token_second = client.get_token()

    assert token_first == "token-123"
    assert token_second == "token-123"
    assert client.call_count == 1


def test_token_refresh_on_expiry():
    client = StubBkashClient()
    token_first = client.get_token()

    client._token_expires_at = time.time() - 10
    token_second = client.get_token()

    assert token_first == "token-123"
    assert token_second == "token-123"
    assert client.call_count == 2
