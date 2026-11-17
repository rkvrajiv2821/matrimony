"""Symmetric sealing for short-lived secrets held in Redis (never in the database)."""

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.common.config import get_settings


@lru_cache
def _fernet() -> Fernet:
    pepper = get_settings().hash_pepper.get_secret_value().encode()
    key = hashlib.sha256(b"vaibhav-sealed-v1:" + pepper).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def seal(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def unseal(token: str, *, ttl_seconds: int) -> str | None:
    try:
        return _fernet().decrypt(token.encode(), ttl=ttl_seconds).decode()
    except InvalidToken:
        return None
