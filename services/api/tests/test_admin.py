from httpx import AsyncClient

from tests.conftest import grant_role, login

ADMIN = "+919000000001"
MEMBER = "+919876543210"


async def test_member_cannot_reach_admin_endpoints(client: AsyncClient) -> None:
    s = await login(client, MEMBER)
    for path in ("/api/v1/admin/feature-flags", "/api/v1/admin/audit-logs"):
        r = await client.get(path, headers=s.headers)
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "permission_denied"


async def test_wrong_role_is_denied(client: AsyncClient) -> None:
    await login(client, ADMIN)
    await grant_role(ADMIN, "content_manager")
    s = await login(client, ADMIN)
    assert (await client.get("/api/v1/admin/feature-flags", headers=s.headers)).status_code == 403


async def test_monetization_flag_defaults_off(client: AsyncClient) -> None:
    await login(client, ADMIN)
    await grant_role(ADMIN, "super_admin")
    s = await login(client, ADMIN)
    flags = (await client.get("/api/v1/admin/feature-flags", headers=s.headers)).json()
    monetization = next(f for f in flags if f["key"] == "monetization_enabled")
    assert monetization["enabled"] is False


async def test_flag_change_is_audited(client: AsyncClient) -> None:
    await login(client, ADMIN)
    await grant_role(ADMIN, "super_admin")
    s = await login(client, ADMIN)
    r = await client.patch(
        "/api/v1/admin/feature-flags/monetization_enabled",
        json={"rollout_percent": 10},
        headers=s.headers,
    )
    assert r.status_code == 200
    assert r.json()["rollout_percent"] == 10
    logs = (
        await client.get("/api/v1/admin/audit-logs?action=feature_flag.update", headers=s.headers)
    ).json()
    assert len(logs["items"]) == 1
    entry = logs["items"][0]
    assert entry["before"] == {"enabled": False, "rollout_percent": 0}
    assert entry["after"] == {"enabled": False, "rollout_percent": 10}


async def test_unknown_flag_404(client: AsyncClient) -> None:
    await login(client, ADMIN)
    await grant_role(ADMIN, "super_admin")
    s = await login(client, ADMIN)
    r = await client.patch(
        "/api/v1/admin/feature-flags/nope", json={"enabled": True}, headers=s.headers
    )
    assert r.status_code == 404


async def test_audit_log_pagination(client: AsyncClient) -> None:
    await login(client, ADMIN)
    await grant_role(ADMIN, "operations_admin")
    s = await login(client, ADMIN)
    for i in range(3):
        await login(client, f"+91981234567{i}")
    page1 = (await client.get("/api/v1/admin/audit-logs?limit=2", headers=s.headers)).json()
    assert len(page1["items"]) == 2 and page1["next_cursor"]
    page2 = (
        await client.get(
            f"/api/v1/admin/audit-logs?limit=2&cursor={page1['next_cursor']}", headers=s.headers
        )
    ).json()
    ids1 = {i["id"] for i in page1["items"]}
    assert ids1.isdisjoint({i["id"] for i in page2["items"]})
