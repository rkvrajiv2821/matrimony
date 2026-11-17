import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.common.config import Settings
from app.common.ids import uuid7


def test_uuid7_is_versioned_and_ordered() -> None:
    ids = [uuid7() for _ in range(50)]
    assert all(u.version == 7 for u in ids)
    assert len(set(ids)) == 50
    assert [u.int >> 80 for u in ids] == sorted(u.int >> 80 for u in ids)


def test_production_refuses_debug_otp_and_weak_secrets() -> None:
    with pytest.raises(ValidationError):
        Settings(env="production", otp_debug_echo=True)
    with pytest.raises(ValidationError):
        Settings(env="production", otp_debug_echo=False)  # default dev secrets
    ok = Settings(env="production", otp_debug_echo=False, jwt_secret="x" * 40, hash_pepper="y" * 40)
    assert ok.otp_debug_echo is False


async def test_health(client: AsyncClient) -> None:
    assert (await client.get("/health")).json() == {"status": "ok"}
    r = await client.get("/health/ready")
    assert r.status_code == 200
    assert r.json()["checks"] == {"database": "ok", "redis": "ok"}


async def test_security_headers_and_request_id(client: AsyncClient) -> None:
    r = await client.get("/health", headers={"X-Request-ID": "abc-123"})
    assert r.headers["X-Request-ID"] == "abc-123"
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    r = await client.get("/health", headers={"X-Request-ID": "bad id with spaces"})
    assert r.headers["X-Request-ID"] != "bad id with spaces"


async def test_unknown_route_uses_error_envelope(client: AsyncClient) -> None:
    r = await client.get("/api/v1/nope")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
