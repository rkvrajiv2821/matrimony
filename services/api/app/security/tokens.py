import uuid
from dataclasses import dataclass
from datetime import timedelta

import jwt

from app.common.config import get_settings
from app.common.errors import NotAuthenticated
from app.common.time import utcnow

ALGORITHM = "HS256"


@dataclass(frozen=True)
class AccessClaims:
    user_id: uuid.UUID
    session_id: uuid.UUID


def issue_access_token(user_id: uuid.UUID, session_id: uuid.UUID) -> str:
    settings = get_settings()
    now = utcnow()
    payload = {
        "iss": settings.jwt_issuer,
        "sub": str(user_id),
        "sid": str(session_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.access_token_ttl_seconds)).timestamp()),
        "typ": "access",
    }
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> AccessClaims:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[ALGORITHM],
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "sub", "sid", "iss"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise NotAuthenticated("Access token expired.", code="token_expired") from exc
    except jwt.PyJWTError as exc:
        raise NotAuthenticated("Invalid access token.", code="invalid_token") from exc
    if payload.get("typ") != "access":
        raise NotAuthenticated("Invalid access token.", code="invalid_token")
    try:
        return AccessClaims(uuid.UUID(payload["sub"]), uuid.UUID(payload["sid"]))
    except ValueError as exc:
        raise NotAuthenticated("Invalid access token.", code="invalid_token") from exc
