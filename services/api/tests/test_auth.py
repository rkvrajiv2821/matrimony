from datetime import timedelta

import pytest
from httpx import AsyncClient

from app.auth import service as auth_service
from app.common.redis import get_redis
from tests.conftest import body_phone, login

PHONE = "+919876543210"


async def _register(client: AsyncClient, phone: str = PHONE) -> dict[str, str]:
    r = await client.post("/api/v1/auth/register", json={"phone": phone})
    assert r.status_code == 202, r.text
    return r.json()


async def _verify(client: AsyncClient, ch: dict[str, str], code: str | None = None, **extra):  # type: ignore[no-untyped-def]
    body = {"challenge_id": ch["challenge_id"], "code": code or ch["debug_code"], **extra}
    return await client.post("/api/v1/auth/otp/verify", json=body)


CONSENT = {"consents": {"terms": True, "privacy": True}}


async def test_register_accepts_local_format_and_masks_phone(client: AsyncClient) -> None:
    ch = await _register(client, "98765 43210")
    assert ch["phone_masked"] == "+91******3210"
    assert ch["expires_in"] == 300
    assert len(ch["debug_code"]) == 6


@pytest.mark.parametrize("phone", ["12345", "+91 12345 67890", "not-a-phone"])
async def test_register_rejects_invalid_phone(client: AsyncClient, phone: str) -> None:
    r = await client.post("/api/v1/auth/register", json={"phone": phone})
    assert r.status_code == 422
    assert r.json()["error"]["code"] in ("invalid_phone", "validation_error")


async def test_register_response_does_not_reveal_existing_account(client: AsyncClient) -> None:
    await login(client, PHONE)
    existing = await _register(client, PHONE)
    new = await _register(client, "+919812345678")
    assert set(existing) == set(new)
    assert existing["expires_in"] == new["expires_in"]


async def test_resend_cooldown(client: AsyncClient) -> None:
    await _register(client)
    r = await client.post("/api/v1/auth/register", json={"phone": PHONE})
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "otp_cooldown"
    assert int(r.headers["Retry-After"]) > 0


async def test_per_phone_hourly_cap(client: AsyncClient) -> None:
    for _ in range(5):
        await _register(client)
        await get_redis().delete(f"otp:cooldown:{PHONE}")
    r = await client.post("/api/v1/auth/register", json={"phone": PHONE})
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "rate_limited"


async def test_new_challenge_invalidates_previous(client: AsyncClient) -> None:
    first = await _register(client)
    await get_redis().delete(f"otp:cooldown:{PHONE}")
    await _register(client)
    r = await _verify(client, first, **CONSENT)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "otp_expired"


async def test_wrong_code_then_lockout(client: AsyncClient) -> None:
    ch = await _register(client)
    wrong = "000000" if ch["debug_code"] != "000000" else "111111"
    for remaining in (4, 3, 2, 1, 0):
        r = await _verify(client, ch, wrong, **CONSENT)
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "otp_invalid"
        assert r.json()["error"]["details"]["attempts_remaining"] == remaining
    r = await _verify(client, ch, **CONSENT)  # even the right code is now refused
    assert r.json()["error"]["code"] == "otp_too_many_attempts"


async def test_new_user_requires_consent_and_can_retry(client: AsyncClient) -> None:
    ch = await _register(client)
    r = await _verify(client, ch)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "consent_required"
    r = await _verify(client, ch, consents={"terms": True, "privacy": False})
    assert r.json()["error"]["code"] == "consent_required"
    r = await _verify(client, ch, language="ta", **CONSENT)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["is_new_user"] is True
    assert body["user"]["preferred_language"] == "ta"
    assert body["user"]["phone_verified"] is True
    assert body["user"]["roles"] == []


async def test_otp_is_single_use(client: AsyncClient) -> None:
    ch = await _register(client)
    assert (await _verify(client, ch, **CONSENT)).status_code == 200
    r = await _verify(client, ch, **CONSENT)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "otp_expired"


async def test_existing_user_login_without_consent_payload(client: AsyncClient) -> None:
    await login(client)
    ch = await _register(client)
    r = await _verify(client, ch)
    assert r.status_code == 200
    assert r.json()["is_new_user"] is False


async def test_me_requires_valid_token(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/users/me")).status_code == 401
    r = await client.get("/api/v1/users/me", headers={"Authorization": "Bearer nope"})
    assert r.json()["error"]["code"] == "invalid_token"
    session = await login(client)
    r = await client.get("/api/v1/users/me", headers=session.headers)
    assert r.status_code == 200
    assert r.json()["phone_masked"] == "+91******3210"
    assert "phone_e164" not in r.json()


async def test_refresh_rotates_token(client: AsyncClient) -> None:
    s = await login(client)
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": s.refresh_token})
    assert r.status_code == 200
    new = r.json()
    assert new["refresh_token"] != s.refresh_token
    r = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {new['access_token']}"}
    )
    assert r.status_code == 200


async def test_parallel_refresh_inside_grace_gets_same_rotation(client: AsyncClient) -> None:
    s = await login(client)
    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": s.refresh_token})
    second = await client.post("/api/v1/auth/refresh", json={"refresh_token": s.refresh_token})
    assert second.status_code == 200
    assert second.json()["refresh_token"] == first.json()["refresh_token"]
    headers = {"Authorization": f"Bearer {second.json()['access_token']}"}
    assert (await client.get("/api/v1/users/me", headers=headers)).status_code == 200
    assert (await client.get("/api/v1/users/me", headers=s.headers)).status_code == 200


async def test_grace_replay_stops_after_a_further_rotation(client: AsyncClient) -> None:
    s = await login(client)
    first = (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": s.refresh_token})
    ).json()
    await client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    # The original token is now two rotations old: no replay, but no revocation either.
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": s.refresh_token})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_refresh_token"


async def test_refresh_reuse_after_grace_revokes_session(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(auth_service, "REFRESH_REUSE_GRACE", timedelta(seconds=-1))
    s = await login(client)
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": s.refresh_token})
    rotated = r.json()["refresh_token"]
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": s.refresh_token})
    assert r.json()["error"]["code"] == "invalid_refresh_token"
    # The whole session is now dead: access token and the legitimately rotated token.
    r = await client.get("/api/v1/users/me", headers=s.headers)
    assert r.json()["error"]["code"] == "session_revoked"
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": rotated})
    assert r.status_code == 401


async def test_logout_revokes_current_session_only(client: AsyncClient) -> None:
    a = await login(client, device_label="phone")
    b = await login(client, device_label="laptop")
    r = await client.post("/api/v1/auth/logout", json={}, headers=a.headers)
    assert r.status_code == 204
    assert (await client.get("/api/v1/users/me", headers=a.headers)).status_code == 401
    assert (await client.get("/api/v1/users/me", headers=b.headers)).status_code == 200
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": a.refresh_token})
    assert r.status_code == 401


async def test_logout_all_devices(client: AsyncClient) -> None:
    a = await login(client, device_label="phone")
    b = await login(client, device_label="laptop")
    await client.post("/api/v1/auth/logout", json={"all_devices": True}, headers=a.headers)
    assert (await client.get("/api/v1/users/me", headers=b.headers)).status_code == 401


async def test_session_list_and_revoke(client: AsyncClient) -> None:
    a = await login(client, device_label="phone")
    b = await login(client, device_label="laptop")
    r = await client.get("/api/v1/auth/sessions", headers=a.headers)
    sessions = r.json()
    assert {s["device_label"] for s in sessions} == {"phone", "laptop"}
    current = [s for s in sessions if s["current"]]
    assert len(current) == 1 and current[0]["device_label"] == "phone"
    other = next(s for s in sessions if not s["current"])
    r = await client.delete(f"/api/v1/auth/sessions/{other['id']}", headers=a.headers)
    assert r.status_code == 204
    assert (await client.get("/api/v1/users/me", headers=b.headers)).status_code == 401


async def test_cannot_revoke_another_users_session(client: AsyncClient) -> None:
    a = await login(client, PHONE)
    b = await login(client, "+919812345678")
    b_sessions = (await client.get("/api/v1/auth/sessions", headers=b.headers)).json()
    r = await client.delete(f"/api/v1/auth/sessions/{b_sessions[0]['id']}", headers=a.headers)
    assert r.status_code == 404
    assert (await client.get("/api/v1/users/me", headers=b.headers)).status_code == 200


async def test_suspended_user_cannot_log_in_or_use_token(client: AsyncClient) -> None:
    from sqlalchemy import text

    from app.database.session import get_sessionmaker

    s = await login(client)
    async with get_sessionmaker()() as db:
        await db.execute(
            text("UPDATE users SET status='suspended' WHERE phone_e164=:p"),
            {"p": body_phone(PHONE)},
        )
        await db.commit()
    r = await client.get("/api/v1/users/me", headers=s.headers)
    assert r.status_code == 403
    ch = await _register(client)
    r = await _verify(client, ch)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "account_inactive"


async def test_login_is_audited(client: AsyncClient) -> None:
    from sqlalchemy import text

    from app.database.session import get_sessionmaker

    await login(client)
    await login(client)
    async with get_sessionmaker()() as db:
        actions = (await db.execute(text("SELECT action FROM audit_logs ORDER BY id"))).scalars()
        assert list(actions) == ["auth.register", "auth.login"]
