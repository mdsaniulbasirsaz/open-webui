import hashlib
import hmac
import secrets

from open_webui.env import WEBUI_SECRET_KEY


def generate_otp(length: int) -> str:
    length = max(4, min(int(length), 10))
    digits = "0123456789"
    return "".join(secrets.choice(digits) for _ in range(length))


def hash_otp(otp: str) -> str:
    key = WEBUI_SECRET_KEY.encode("utf-8")
    return hmac.new(key, otp.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_otp(otp: str, otp_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(otp), otp_hash)
