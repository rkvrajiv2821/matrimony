import os

os.environ.setdefault("VAIBHAV_ENV", "test")
os.environ.setdefault(
    "VAIBHAV_DATABASE_URL",
    os.environ.get(
        "VAIBHAV_TEST_DATABASE_URL",
        "mysql+asyncmy://vaibhav:vaibhav@127.0.0.1:3306/vaibhav_test?charset=utf8mb4",
    ),
)
os.environ.setdefault("VAIBHAV_REDIS_URL", "redis://127.0.0.1:6379/15")
os.environ["VAIBHAV_OTP_DEBUG_ECHO"] = "true"

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.common.config import get_settings
from app.common.redis import get_redis
from app.database.session import get_sessionmaker

MUTABLE_TABLES = [
    "audit_logs",
    "consents",
    "user_entitlements",
    "user_roles",
    "user_sessions",
    "users",
]


def _alembic_config() -> Config:
    here = os.path.dirname(os.path.dirname(__file__))
    cfg = Config(os.path.join(here, "alembic.ini"))
    cfg.attributes["database_url"] = get_settings().database_url
    return cfg


@pytest.fixture(scope="session", autouse=True)
def migrated_db() -> None:
    """Exercise the real migrations: down to base, then up to head."""
    import threading

    def run() -> None:
        cfg = _alembic_config()
        command.downgrade(cfg, "base")
        command.upgrade(cfg, "head")

    # Alembic's env.py calls asyncio.run(); run it off the pytest event loop thread.
    errors: list[BaseException] = []

    def guarded() -> None:
        try:
            run()
        except BaseException as exc:
            errors.append(exc)

    t = threading.Thread(target=guarded)
    t.start()
    t.join()
    if errors:
        raise errors[0]


@pytest.fixture(autouse=True)
async def clean_state() -> AsyncIterator[None]:
    await get_redis().flushdb()
    async with get_sessionmaker()() as db:
        await db.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for table in MUTABLE_TABLES:
            await db.execute(text(f"DELETE FROM {table}"))  # noqa: S608
        await db.execute(text("UPDATE feature_flags SET enabled=0, rollout_percent=0"))
        await db.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        await db.commit()
    yield


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@dataclass
class LoggedIn:
    access_token: str
    refresh_token: str
    user: dict[str, Any]

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}


async def login(
    client: AsyncClient, phone: str = "+919876543210", *, device_label: str = "pytest"
) -> LoggedIn:
    r = await client.post("/api/v1/auth/register", json={"phone": phone})
    assert r.status_code == 202, r.text
    ch = r.json()
    r = await client.post(
        "/api/v1/auth/otp/verify",
        json={
            "challenge_id": ch["challenge_id"],
            "code": ch["debug_code"],
            "consents": {"terms": True, "privacy": True},
            "device_label": device_label,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Clear the resend cooldown so tests can log the same phone in again immediately.
    await get_redis().delete(f"otp:cooldown:{body_phone(phone)}")
    return LoggedIn(body["access_token"], body["refresh_token"], body["user"])


def body_phone(phone: str) -> str:
    from app.common.phone import normalize_phone

    return normalize_phone(phone)


async def grant_role(phone: str, role: str) -> None:
    async with get_sessionmaker()() as db:
        await db.execute(
            text(
                "INSERT INTO user_roles (user_id, role_id, created_at) "
                "SELECT u.id, r.id, UTC_TIMESTAMP(6) FROM users u, roles r "
                "WHERE u.phone_e164 = :p AND r.code = :r"
            ),
            {"p": body_phone(phone), "r": role},
        )
        await db.commit()
