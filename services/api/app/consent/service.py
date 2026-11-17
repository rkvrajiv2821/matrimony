from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import get_settings
from app.common.time import utcnow
from app.consent.models import REQUIRED_CONSENTS, Consent, ConsentType


def current_policy_version(consent_type: ConsentType) -> str:
    s = get_settings()
    if consent_type == ConsentType.TERMS:
        return s.terms_policy_version
    if consent_type == ConsentType.PRIVACY:
        return s.privacy_policy_version
    return "v1"


async def active_consents(db: AsyncSession, user_id: int) -> list[Consent]:
    stmt = (
        select(Consent)
        .where(Consent.user_id == user_id, Consent.withdrawn_at.is_(None))
        .order_by(Consent.granted_at.desc(), Consent.id.desc())
    )
    return list((await db.scalars(stmt)).all())


async def missing_required(db: AsyncSession, user_id: int) -> set[ConsentType]:
    """Required consents not yet granted for the *current* policy versions."""
    granted = {
        (c.consent_type, c.policy_version) for c in await active_consents(db, user_id) if c.granted
    }
    return {t for t in REQUIRED_CONSENTS if (t.value, current_policy_version(t)) not in granted}


async def record(
    db: AsyncSession, user_id: int, consent_type: ConsentType, granted: bool, source: str
) -> Consent:
    """Record a decision. A newer decision for the same type supersedes (withdraws) older ones."""
    now = utcnow()
    for c in await active_consents(db, user_id):
        if c.consent_type == consent_type.value:
            c.withdrawn_at = now
    consent = Consent(
        user_id=user_id,
        consent_type=consent_type.value,
        policy_version=current_policy_version(consent_type),
        granted=granted,
        source=source,
        granted_at=now,
    )
    db.add(consent)
    await db.flush()
    return consent
