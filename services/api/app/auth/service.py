from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit
from app.auth import otp
from app.auth.models import UserSession
from app.auth.schemas import ConsentChoices
from app.common.config import get_settings
from app.common.errors import AppError, NotAuthenticated, PermissionDenied
from app.common.redis import get_redis
from app.common.time import utcnow
from app.consent import service as consents
from app.consent.models import ConsentType
from app.security.deps import RequestMeta
from app.security.hashing import keyed_hash, new_refresh_token
from app.security.sealed import seal, unseal
from app.security.tokens import issue_access_token
from app.users.models import Language, User, UserStatus

# A rotated-out refresh token presented within this window is treated as a benign race
# (parallel requests from the same client), not theft.
REFRESH_REUSE_GRACE = timedelta(seconds=30)


class ConsentRequired(AppError):
    code = "consent_required"
    message = "Please accept the Terms of Use and Privacy Notice to continue."


@dataclass
class IssuedTokens:
    access_token: str
    refresh_token: str
    session: UserSession


def _hash_refresh(token: str) -> str:
    return keyed_hash("refresh", token)


async def _create_session(
    db: AsyncSession, user: User, meta: RequestMeta, device_id: str | None, label: str | None
) -> IssuedTokens:
    s = get_settings()
    refresh = new_refresh_token()
    now = utcnow()
    session = UserSession(
        user_id=user.id,
        refresh_token_hash=_hash_refresh(refresh),
        device_id=device_id,
        device_label=label or (meta.user_agent or "")[:150] or None,
        ip_hash=meta.ip_hash,
        last_used_at=now,
        expires_at=now + timedelta(seconds=s.refresh_token_ttl_seconds),
    )
    db.add(session)
    await db.flush()
    return IssuedTokens(issue_access_token(user.public_id, session.public_id), refresh, session)


async def verify_otp_and_login(
    db: AsyncSession,
    *,
    challenge_id: str,
    code: str,
    consent_choices: ConsentChoices | None,
    language: Language | None,
    device_id: str | None,
    device_label: str | None,
    meta: RequestMeta,
) -> tuple[User, IssuedTokens, bool]:
    verified = await otp.peek(challenge_id, code)
    phone = verified.phone_e164

    user = await db.scalar(select(User).where(User.phone_e164 == phone).with_for_update())
    is_new = user is None

    # Consent is checked before consuming the OTP so the client can resubmit with consent.
    choices = consent_choices or ConsentChoices()
    if is_new:
        if not (choices.terms and choices.privacy):
            raise ConsentRequired(details={"missing": ["privacy", "terms"]})
    else:
        assert user is not None
        if user.status in (UserStatus.SUSPENDED, UserStatus.DELETED):
            await otp.consume(verified)
            raise PermissionDenied("This account is not available.", code="account_inactive")
        missing = await consents.missing_required(db, user.id)
        if missing and not all(getattr(choices, m.value) for m in missing):
            raise ConsentRequired(details={"missing": sorted(m.value for m in missing)})

    await otp.consume(verified)
    now = utcnow()

    if user is None:
        user = User(
            phone_e164=phone,
            status=UserStatus.ACTIVE,
            preferred_language=(language or Language.EN).value,
            phone_verified_at=now,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user, ["roles"])
    elif user.status == UserStatus.DEACTIVATED:
        user.status = UserStatus.ACTIVE  # logging in reactivates a self-deactivated account

    user.last_login_at = now
    user.phone_verified_at = user.phone_verified_at or now

    missing = await consents.missing_required(db, user.id)
    for consent_type in missing:
        await consents.record(db, user.id, consent_type, True, source="registration")
    if choices.marketing is not None:
        await consents.record(db, user.id, ConsentType.MARKETING, choices.marketing, "registration")

    tokens = await _create_session(db, user, meta, device_id, device_label)
    await audit.record(
        db,
        action="auth.register" if is_new else "auth.login",
        resource_type="user",
        resource_id=str(user.public_id),
        actor_user_id=user.id,
        after={"session": str(tokens.session.public_id)},
        ip_hash=meta.ip_hash,
        request_id=meta.request_id,
    )
    return user, tokens, is_new


async def refresh(db: AsyncSession, refresh_token: str, meta: RequestMeta) -> IssuedTokens:
    s = get_settings()
    token_hash = _hash_refresh(refresh_token)
    now = utcnow()

    session = await db.scalar(
        select(UserSession).where(UserSession.refresh_token_hash == token_hash).with_for_update()
    )
    if session is None:
        reused = await db.scalar(
            select(UserSession)
            .where(UserSession.previous_refresh_token_hash == token_hash)
            .with_for_update()
        )
        if reused is not None and reused.revoked_at is None:
            if reused.last_used_at and now - reused.last_used_at <= REFRESH_REUSE_GRACE:
                replay = await _replay_rotation(db, reused, token_hash)
                if replay is not None:
                    return replay
                raise NotAuthenticated(
                    "Refresh token was already rotated.", code="refresh_token_superseded"
                )
            reused.revoked_at = now
            reused.revoked_reason = "refresh_reuse"
            await audit.record(
                db,
                action="auth.refresh_reuse_detected",
                resource_type="user_session",
                resource_id=str(reused.public_id),
                actor_user_id=reused.user_id,
                ip_hash=meta.ip_hash,
                request_id=meta.request_id,
            )
            await db.commit()  # persist the revocation even though we raise
        raise NotAuthenticated("Invalid refresh token.", code="invalid_refresh_token")

    if session.revoked_at is not None or session.expires_at <= now:
        raise NotAuthenticated("Session has ended.", code="session_revoked")

    user = await db.get(User, session.user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise NotAuthenticated("Session has ended.", code="session_revoked")

    new_token = new_refresh_token()
    session.previous_refresh_token_hash = session.refresh_token_hash
    session.refresh_token_hash = _hash_refresh(new_token)
    session.last_used_at = now
    session.ip_hash = meta.ip_hash
    session.expires_at = now + timedelta(seconds=s.refresh_token_ttl_seconds)
    await db.flush()
    # Parallel requests from the same client may present the old token a moment later;
    # let them receive this same rotation instead of being logged out.
    grace_seconds = int(REFRESH_REUSE_GRACE.total_seconds())
    if grace_seconds > 0:
        await get_redis().set(_grace_key(token_hash), seal(new_token), ex=grace_seconds)
    return IssuedTokens(issue_access_token(user.public_id, session.public_id), new_token, session)


def _grace_key(old_hash: str) -> str:
    return f"refresh:grace:{old_hash}"


async def _replay_rotation(
    db: AsyncSession, session: UserSession, old_hash: str
) -> IssuedTokens | None:
    sealed = await get_redis().get(_grace_key(old_hash))
    if not sealed:
        return None
    token = unseal(str(sealed), ttl_seconds=int(REFRESH_REUSE_GRACE.total_seconds()))
    # Only replay if that rotation is still the session's current one.
    if token is None or _hash_refresh(token) != session.refresh_token_hash:
        return None
    user = await db.get(User, session.user_id)
    if user is None or user.status != UserStatus.ACTIVE or session.expires_at <= utcnow():
        return None
    return IssuedTokens(issue_access_token(user.public_id, session.public_id), token, session)


async def revoke_sessions(
    db: AsyncSession, user: User, *, only: UserSession | None, reason: str, meta: RequestMeta
) -> int:
    now = utcnow()
    stmt = (
        update(UserSession)
        .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        .values(revoked_at=now, revoked_reason=reason)
    )
    if only is not None:
        stmt = stmt.where(UserSession.id == only.id)
    result = await db.execute(stmt)
    count = int(getattr(result, "rowcount", 0) or 0)
    await audit.record(
        db,
        action="auth.logout_all" if only is None else "auth.logout",
        resource_type="user",
        resource_id=str(user.public_id),
        actor_user_id=user.id,
        after={"revoked": count, "reason": reason},
        ip_hash=meta.ip_hash,
        request_id=meta.request_id,
    )
    return count
