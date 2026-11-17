import hashlib
import hmac
import secrets

from app.common.config import get_settings


def keyed_hash(purpose: str, value: str) -> str:
    pepper = get_settings().hash_pepper.get_secret_value().encode()
    return hmac.new(pepper, f"{purpose}:{value}".encode(), hashlib.sha256).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def new_otp(length: int) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(length))
