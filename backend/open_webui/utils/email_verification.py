import hashlib
import hmac
import secrets

from open_webui.env import WEBUI_SECRET_KEY


def generate_otp(length: int) -> str:
    length = max(4, min(int(length), 10))
    digits = "0123456789"
    return "".join(secrets.choice(digits) for _ in range(length))


def _hash_value(value: str) -> str:
    key = WEBUI_SECRET_KEY.encode("utf-8")
    return hmac.new(key, value.encode("utf-8"), hashlib.sha256).hexdigest()


def hash_otp(otp: str) -> str:
    return _hash_value(otp)


def verify_otp(otp: str, otp_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(otp), otp_hash)


def generate_verification_token(byte_length: int = 32) -> str:
    byte_length = max(16, min(int(byte_length), 64))
    return secrets.token_urlsafe(byte_length)


def hash_verification_token(token: str) -> str:
    return _hash_value(token)


def verify_verification_token(token: str, token_hash: str) -> bool:
    return hmac.compare_digest(hash_verification_token(token), token_hash)
