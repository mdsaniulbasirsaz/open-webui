import logging
import time
from typing import Any, Optional

import requests

log = logging.getLogger(__name__)


class BkashClient:
    def __init__(
        self,
        base_url: str,
        app_key: str,
        app_secret: str,
        username: str,
        password: str,
        timeout_seconds: int = 30,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/" if base_url else ""
        self.app_key = app_key
        self.app_secret = app_secret
        self.username = username
        self.password = password
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()
        self._token: Optional[str] = None
        self._token_expires_at = 0.0

    def _build_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self.base_url}{path.lstrip('/')}"

    def _token_valid(self) -> bool:
        if not self._token:
            return False
        return time.time() < (self._token_expires_at - 30)

    def _base_has_checkout(self) -> bool:
        base = self.base_url.lower()
        return "/checkout/" in base or base.rstrip("/").endswith("/checkout")

    def _checkout_path(self, suffix: str) -> str:
        suffix = suffix.lstrip("/")
        if self._base_has_checkout():
            return suffix
        return f"checkout/{suffix}"

    def _grant_token(self) -> str:
        if not self.base_url:
            raise ValueError("BKASH_BASE_URL is required")

        payload = {"app_key": self.app_key, "app_secret": self.app_secret}
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "username": self.username,
            "password": self.password,
            "X-APP-Key": self.app_key,
        }

        response = self._request(
            "POST",
            self._checkout_path("token/grant"),
            json=payload,
            headers=headers,
            require_auth=False,
            retries=1,
        )
        response.raise_for_status()
        data = response.json()

        token = data.get("id_token") or data.get("access_token") or data.get("token")
        if not token:
            raise ValueError("bKash token grant response missing token")

        expires_in = data.get("expires_in") or 0
        try:
            expires_in = int(expires_in)
        except (TypeError, ValueError):
            expires_in = 0
        if expires_in <= 0:
            expires_in = 3000

        self._token = token
        self._token_expires_at = time.time() + expires_in
        log.info("bKash token granted; expires_in=%s", expires_in)
        return token

    def get_token(self) -> str:
        if self._token_valid():
            return self._token or ""
        return self._grant_token()

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": self.get_token(), "X-APP-Key": self.app_key}

    def _request(
        self,
        method: str,
        path: str,
        json: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        require_auth: bool = True,
        retries: int = 0,
    ) -> requests.Response:
        url = self._build_url(path)
        request_headers = {"Accept": "application/json"}
        if json is not None:
            request_headers.setdefault("Content-Type", "application/json")
        if headers:
            request_headers.update(headers)
        if require_auth:
            request_headers.update(self._auth_headers())

        attempt = 0
        refreshed = False
        while True:
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    json=json,
                    params=params,
                    headers=request_headers,
                    timeout=self.timeout_seconds,
                )
            except requests.RequestException as exc:
                if attempt < retries and method.upper() in {"GET", "POST"}:
                    delay = 0.5 * (2**attempt)
                    log.warning("bKash request failed; retrying in %.1fs", delay)
                    time.sleep(delay)
                    attempt += 1
                    continue
                raise exc

            if require_auth and response.status_code in {401, 403} and not refreshed:
                self._token = None
                self._token_expires_at = 0.0
                request_headers.update(self._auth_headers())
                refreshed = True
                continue

            if response.status_code >= 500 and attempt < retries and method.upper() in {
                "GET",
                "POST",
            }:
                delay = 0.5 * (2**attempt)
                log.warning(
                    "bKash response %s; retrying in %.1fs",
                    response.status_code,
                    delay,
                )
                time.sleep(delay)
                attempt += 1
                continue

            return response

    def create_payment(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._request(
            "POST", self._checkout_path("create"), json=payload, retries=1
        )
        response.raise_for_status()
        return response.json()

    def execute_payment(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._request(
            "POST", self._checkout_path("execute"), json=payload, retries=1
        )
        response.raise_for_status()
        return response.json()

    def query_payment(self, payment_id: str) -> dict[str, Any]:
        response = self._request(
            "GET",
            self._checkout_path("payment/status"),
            params={"paymentID": payment_id},
        )
        response.raise_for_status()
        return response.json()
