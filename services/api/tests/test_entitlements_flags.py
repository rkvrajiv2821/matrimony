import ast
from datetime import timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text

from app.common.time import utcnow
from app.database.session import get_sessionmaker
from app.entitlements import service as ent
from app.entitlements.models import UserEntitlement
from app.flags import service as flags
from app.users.models import User
from tests.conftest import body_phone, login

APP_DIR = Path(__file__).resolve().parent.parent / "app"

# PRD v1.1 §5: these must never be paywalled, so they must never consult entitlements.
NEVER_GATED_PACKAGES = {"safety", "privacy", "support", "consent", "auth", "reports", "blocks"}
# PRD v1.1 §2: payment state must never influence ranking.
RANKING_PACKAGES = {"discovery", "matching", "search"}
MONEY_MODULES = ("app.entitlements", "app.monetization")


def _imports(pkg: Path) -> set[str]:
    found: set[str] = set()
    for f in pkg.rglob("*.py"):
        for node in ast.walk(ast.parse(f.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module:
                found.add(node.module)
                found.update(f"{node.module}.{a.name}" for a in node.names)
            elif isinstance(node, ast.Import):
                found.update(a.name for a in node.names)
    return found


@pytest.mark.parametrize("pkg", sorted(NEVER_GATED_PACKAGES | RANKING_PACKAGES))
def test_protected_modules_never_import_entitlements_or_payments(pkg: str) -> None:
    path = APP_DIR / pkg
    if not path.exists():
        pytest.skip(f"app/{pkg} not built yet")
    leaked = {m for m in _imports(path) if m.startswith(MONEY_MODULES)}
    assert not leaked, f"app/{pkg} must not depend on {leaked}"


async def _user(phone: str) -> User:
    async with get_sessionmaker()() as db:
        user = await db.scalar(select(User).where(User.phone_e164 == body_phone(phone)))
        assert user is not None
        return user


async def test_free_plan_grants_all_core_entitlements(client: AsyncClient) -> None:
    await login(client)
    user = await _user("+919876543210")
    async with get_sessionmaker()() as db:
        resolved = await ent.resolve(db, user)
        assert set(resolved) == ent.CORE_ENTITLEMENTS
        for key in ent.Entitlement:
            await ent.require_entitlement(db, user, key)


async def test_user_grant_overrides_and_expires(client: AsyncClient) -> None:
    await login(client)
    user = await _user("+919876543210")
    async with get_sessionmaker()() as db:
        db.add(
            UserEntitlement(
                user_id=user.id,
                entitlement_key="messaging.send",
                value_json={"enabled": False},
                source="moderation",
                starts_at=utcnow() - timedelta(minutes=1),
            )
        )
        db.add(
            UserEntitlement(
                user_id=user.id,
                entitlement_key="search.use",
                value_json=False,
                source="test",
                starts_at=utcnow() - timedelta(days=2),
                expires_at=utcnow() - timedelta(days=1),
            )
        )
        await db.commit()
        assert not await ent.has_entitlement(db, user, ent.Entitlement.MESSAGING_SEND)
        assert await ent.has_entitlement(db, user, ent.Entitlement.SEARCH_USE)  # grant expired
        with pytest.raises(Exception) as exc:
            await ent.require_entitlement(db, user, ent.Entitlement.MESSAGING_SEND)
        assert getattr(exc.value, "code", None) == "feature_unavailable"
        assert "plan" not in str(exc.value).lower() and "upgrade" not in str(exc.value).lower()


async def test_unknown_flag_is_off_and_monetization_off_by_default() -> None:
    async with get_sessionmaker()() as db:
        assert await flags.is_enabled(db, "does_not_exist") is False
        assert await flags.is_enabled(db, flags.MONETIZATION_ENABLED, subject="u1") is False


async def test_rollout_percent_is_deterministic() -> None:
    async with get_sessionmaker()() as db:
        await db.execute(
            text("UPDATE feature_flags SET enabled=1, rollout_percent=50 WHERE `key`=:k"),
            {"k": flags.MONETIZATION_ENABLED},
        )
        await db.commit()
        results = [
            await flags.is_enabled(db, flags.MONETIZATION_ENABLED, subject=f"user-{i}")
            for i in range(200)
        ]
        again = [
            await flags.is_enabled(db, flags.MONETIZATION_ENABLED, subject=f"user-{i}")
            for i in range(200)
        ]
        assert results == again
        assert 60 < sum(results) < 140
        assert await flags.is_enabled(db, flags.MONETIZATION_ENABLED) is False  # no subject
