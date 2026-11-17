from httpx import AsyncClient

from tests.conftest import login


async def test_update_language(client: AsyncClient) -> None:
    s = await login(client)
    r = await client.patch(
        "/api/v1/users/me", json={"preferred_language": "ta-Latn"}, headers=s.headers
    )
    assert r.status_code == 200
    assert r.json()["preferred_language"] == "ta-Latn"
    r = await client.patch("/api/v1/users/me", json={"preferred_language": "fr"}, headers=s.headers)
    assert r.status_code == 422


async def test_email_is_unique_and_unverified(client: AsyncClient) -> None:
    a = await login(client, "+919876543210")
    b = await login(client, "+919812345678")
    r = await client.patch(
        "/api/v1/users/me", json={"email": "Asha@Example.com"}, headers=a.headers
    )
    assert r.json()["email"] == "asha@example.com"
    assert r.json()["email_verified"] is False
    r = await client.patch(
        "/api/v1/users/me", json={"email": "asha@example.com"}, headers=b.headers
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "email_taken"


async def test_registration_records_required_consents(client: AsyncClient) -> None:
    s = await login(client)
    consents = (await client.get("/api/v1/users/me/consents", headers=s.headers)).json()
    assert {c["consent_type"] for c in consents} == {"terms", "privacy"}
    assert all(c["granted"] for c in consents)


async def test_marketing_consent_grant_and_withdraw(client: AsyncClient) -> None:
    s = await login(client)
    r = await client.post(
        "/api/v1/consents", json={"consent_type": "marketing", "granted": True}, headers=s.headers
    )
    assert r.status_code == 201
    cid = r.json()["id"]
    r = await client.delete(f"/api/v1/consents/{cid}", headers=s.headers)
    assert r.status_code == 204
    consents = (await client.get("/api/v1/users/me/consents", headers=s.headers)).json()
    assert "marketing" not in {c["consent_type"] for c in consents}


async def test_required_consent_cannot_be_withdrawn_or_declined(client: AsyncClient) -> None:
    s = await login(client)
    consents = (await client.get("/api/v1/users/me/consents", headers=s.headers)).json()
    terms = next(c for c in consents if c["consent_type"] == "terms")
    r = await client.delete(f"/api/v1/consents/{terms['id']}", headers=s.headers)
    assert r.json()["error"]["code"] == "consent_required_for_service"
    r = await client.post(
        "/api/v1/consents", json={"consent_type": "privacy", "granted": False}, headers=s.headers
    )
    assert r.json()["error"]["code"] == "consent_required_for_service"


async def test_cannot_withdraw_another_users_consent(client: AsyncClient) -> None:
    a = await login(client, "+919876543210")
    b = await login(client, "+919812345678")
    r = await client.post(
        "/api/v1/consents", json={"consent_type": "marketing", "granted": True}, headers=b.headers
    )
    r = await client.delete(f"/api/v1/consents/{r.json()['id']}", headers=a.headers)
    assert r.status_code == 404
