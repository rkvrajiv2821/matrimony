import uuid

from fastapi import APIRouter, status
from sqlalchemy import select

from app.auth import otp, service
from app.auth.models import UserSession
from app.auth.schemas import (
    AuthResultOut,
    LogoutIn,
    OtpChallengeOut,
    OtpRequestIn,
    OtpResendIn,
    OtpVerifyIn,
    RefreshIn,
    SessionOut,
    TokenPairOut,
)
from app.auth.sms import get_sms_provider
from app.common.config import get_settings
from app.common.errors import NotFound
from app.common.phone import mask_phone, normalize_phone
from app.common.time import utcnow
from app.security.deps import DB, Auth, Meta
from app.users.models import Language
from app.users.schemas import MeOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _challenge_out(phone: str, issued: otp.IssuedChallenge) -> OtpChallengeOut:
    return OtpChallengeOut(
        challenge_id=issued.challenge_id,
        expires_in=issued.expires_in,
        resend_after=issued.resend_after,
        phone_masked=mask_phone(phone),
        debug_code=issued.code if get_settings().otp_debug_echo else None,
    )


@router.post("/register", response_model=OtpChallengeOut, status_code=status.HTTP_202_ACCEPTED)
async def register(body: OtpRequestIn, meta: Meta) -> OtpChallengeOut:
    """Start sign-up or sign-in with a mobile number.

    The response is identical whether or not the number already has an account
    (prevents account enumeration).
    """
    phone = normalize_phone(body.phone)
    issued = await otp.issue(phone, meta.ip_hash)
    await get_sms_provider().send_otp(phone, issued.code, body.language.value)
    return _challenge_out(phone, issued)


@router.post("/otp/resend", response_model=OtpChallengeOut, status_code=status.HTTP_202_ACCEPTED)
async def resend(body: OtpResendIn, meta: Meta) -> OtpChallengeOut:
    phone, issued = await otp.resend(body.challenge_id, meta.ip_hash)
    await get_sms_provider().send_otp(phone, issued.code, Language.EN.value)
    return _challenge_out(phone, issued)


@router.post("/otp/verify", response_model=AuthResultOut)
async def verify(body: OtpVerifyIn, db: DB, meta: Meta) -> AuthResultOut:
    user, tokens, is_new = await service.verify_otp_and_login(
        db,
        challenge_id=body.challenge_id,
        code=body.code,
        consent_choices=body.consents,
        language=body.language,
        device_id=body.device_id,
        device_label=body.device_label,
        meta=meta,
    )
    return AuthResultOut(
        access_token=tokens.access_token,
        access_token_expires_in=get_settings().access_token_ttl_seconds,
        refresh_token=tokens.refresh_token,
        refresh_token_expires_at=tokens.session.expires_at,
        is_new_user=is_new,
        user=MeOut.from_user(user),
    )


@router.post("/refresh", response_model=TokenPairOut)
async def refresh(body: RefreshIn, db: DB, meta: Meta) -> TokenPairOut:
    tokens = await service.refresh(db, body.refresh_token, meta)
    return TokenPairOut(
        access_token=tokens.access_token,
        access_token_expires_in=get_settings().access_token_ttl_seconds,
        refresh_token=tokens.refresh_token,
        refresh_token_expires_at=tokens.session.expires_at,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: LogoutIn, auth: Auth, db: DB, meta: Meta) -> None:
    await service.revoke_sessions(
        db,
        auth.user,
        only=None if body.all_devices else auth.session,
        reason="logout_all" if body.all_devices else "logout",
        meta=meta,
    )


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(auth: Auth, db: DB) -> list[SessionOut]:
    rows = await db.scalars(
        select(UserSession)
        .where(
            UserSession.user_id == auth.user.id,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > utcnow(),
        )
        .order_by(UserSession.last_used_at.desc())
    )
    return [
        SessionOut(
            id=s.public_id,
            device_label=s.device_label,
            created_at=s.created_at,
            last_used_at=s.last_used_at,
            expires_at=s.expires_at,
            current=s.id == auth.session.id,
        )
        for s in rows
    ]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(session_id: uuid.UUID, auth: Auth, db: DB, meta: Meta) -> None:
    target = await db.scalar(
        select(UserSession).where(
            UserSession.public_id == session_id,
            UserSession.user_id == auth.user.id,  # resource-level authorization
            UserSession.revoked_at.is_(None),
        )
    )
    if target is None:
        raise NotFound()
    await service.revoke_sessions(db, auth.user, only=target, reason="revoked_by_user", meta=meta)
