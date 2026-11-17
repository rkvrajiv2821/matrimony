from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import UserSession
from app.common.errors import NotAuthenticated, PermissionDenied
from app.common.request import client_ip, ip_hash
from app.common.time import utcnow
from app.database.session import get_db
from app.security.roles import RoleCode
from app.security.tokens import decode_access_token
from app.users.models import User, UserStatus

_bearer = HTTPBearer(auto_error=False)

DB = Annotated[AsyncSession, Depends(get_db)]


@dataclass
class AuthContext:
    user: User
    session: UserSession


async def get_auth(
    db: DB,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise NotAuthenticated()
    claims = decode_access_token(credentials.credentials)
    row = (
        await db.execute(
            select(User, UserSession)
            .join(UserSession, UserSession.user_id == User.id)
            .where(User.public_id == claims.user_id, UserSession.public_id == claims.session_id)
        )
    ).first()
    if row is None:
        raise NotAuthenticated("Session not found.", code="invalid_session")
    user, session = row
    if session.revoked_at is not None or session.expires_at <= utcnow():
        raise NotAuthenticated("Session has ended.", code="session_revoked")
    if user.status != UserStatus.ACTIVE:
        raise PermissionDenied("This account is not active.", code="account_inactive")
    return AuthContext(user=user, session=session)


Auth = Annotated[AuthContext, Depends(get_auth)]


def require_roles(*roles: RoleCode) -> Callable[[AuthContext], Awaitable[AuthContext]]:
    """Deny unless the caller holds at least one of `roles` (super_admin always passes)."""
    allowed = {r.value for r in roles} | {RoleCode.SUPER_ADMIN.value}

    async def _dep(auth: Auth) -> AuthContext:
        if not (auth.user.role_codes & allowed):
            raise PermissionDenied()
        return auth

    return _dep


@dataclass
class RequestMeta:
    ip: str
    ip_hash: str
    request_id: str | None
    user_agent: str | None


def get_request_meta(request: Request) -> RequestMeta:
    ip = client_ip(request)
    return RequestMeta(
        ip=ip,
        ip_hash=ip_hash(ip),
        request_id=getattr(request.state, "request_id", None),
        user_agent=request.headers.get("user-agent"),
    )


Meta = Annotated[RequestMeta, Depends(get_request_meta)]
