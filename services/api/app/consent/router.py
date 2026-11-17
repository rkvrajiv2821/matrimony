import uuid
from datetime import datetime

from fastapi import APIRouter, status
from pydantic import BaseModel
from sqlalchemy import select

from app.audit import service as audit
from app.common.errors import AppError, NotFound
from app.common.time import utcnow
from app.consent import service
from app.consent.models import REQUIRED_CONSENTS, Consent, ConsentType
from app.security.deps import DB, Auth, Meta

router = APIRouter(tags=["consent"])


class ConsentOut(BaseModel):
    id: uuid.UUID
    consent_type: ConsentType
    policy_version: str
    granted: bool
    granted_at: datetime

    @classmethod
    def of(cls, c: Consent) -> "ConsentOut":
        return cls(
            id=c.public_id,
            consent_type=ConsentType(c.consent_type),
            policy_version=c.policy_version,
            granted=c.granted,
            granted_at=c.granted_at,
        )


class ConsentIn(BaseModel):
    consent_type: ConsentType
    granted: bool


@router.get("/users/me/consents", response_model=list[ConsentOut])
async def list_consents(auth: Auth, db: DB) -> list[ConsentOut]:
    return [ConsentOut.of(c) for c in await service.active_consents(db, auth.user.id)]


@router.post("/consents", response_model=ConsentOut, status_code=status.HTTP_201_CREATED)
async def give_consent(body: ConsentIn, auth: Auth, db: DB, meta: Meta) -> ConsentOut:
    if body.consent_type in REQUIRED_CONSENTS and not body.granted:
        raise AppError(
            "Required notices cannot be declined here. To stop using VAIBHAV, delete your account.",
            code="consent_required_for_service",
        )
    consent = await service.record(db, auth.user.id, body.consent_type, body.granted, "settings")
    await audit.record(
        db,
        action="consent.record",
        resource_type="consent",
        resource_id=str(consent.public_id),
        actor_user_id=auth.user.id,
        after={"type": body.consent_type.value, "granted": body.granted},
        ip_hash=meta.ip_hash,
        request_id=meta.request_id,
    )
    return ConsentOut.of(consent)


@router.delete("/consents/{consent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw_consent(consent_id: uuid.UUID, auth: Auth, db: DB, meta: Meta) -> None:
    consent = await db.scalar(
        select(Consent).where(
            Consent.public_id == consent_id,
            Consent.user_id == auth.user.id,
            Consent.withdrawn_at.is_(None),
        )
    )
    if consent is None:
        raise NotFound()
    if consent.consent_type in {c.value for c in REQUIRED_CONSENTS}:
        raise AppError(
            "Required notices cannot be withdrawn here. "
            "To stop using VAIBHAV, delete your account.",
            code="consent_required_for_service",
        )
    consent.withdrawn_at = utcnow()
    await audit.record(
        db,
        action="consent.withdraw",
        resource_type="consent",
        resource_id=str(consent.public_id),
        actor_user_id=auth.user.id,
        ip_hash=meta.ip_hash,
        request_id=meta.request_id,
    )
