import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.flags.models import FeatureFlag

MONETIZATION_ENABLED = "monetization_enabled"


def _bucket(key: str, subject: str) -> int:
    digest = hashlib.sha256(f"{key}:{subject}".encode()).digest()
    return int.from_bytes(digest[:4], "big") % 100


async def is_enabled(db: AsyncSession, key: str, *, subject: str | None = None) -> bool:
    """A flag is on when enabled and, for partial rollouts, the subject falls inside the bucket.

    Unknown flags are off (deny by default).
    """
    flag = await db.scalar(select(FeatureFlag).where(FeatureFlag.key == key))
    if flag is None or not flag.enabled:
        return False
    if flag.rollout_percent >= 100:
        return True
    if subject is None:
        return False
    return _bucket(key, subject) < flag.rollout_percent
