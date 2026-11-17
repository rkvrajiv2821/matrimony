from httpx import AsyncClient

from tests.conftest import grant_role, login
from tests.profile_helpers import (
    BASIC,
    MODERATOR_PHONE,
    complete_profile,
    create_profile,
    moderator,
    put,
    upload_photo,
)

A = "+919876543210"
PARENT = "+919811111111"
DAUGHTER = "+919822222222"
MOTHER = "+919833333333"


# ------------------------------------------------------------------ moderation


async def _submitted(client: AsyncClient, phone: str = A) -> tuple[object, str, list[dict]]:
    s = await login(client, phone)
    pid = (await create_profile(client, s))["id"]
    await complete_profile(client, s, pid)
    r = await client.post(f"/api/v1/profiles/{pid}/submit", headers=s.headers)
    return s, pid, r.json()["photos"]


async def test_members_cannot_moderate(client: AsyncClient) -> None:
    s, pid, _ = await _submitted(client)
    assert (await client.get("/api/v1/admin/profiles", headers=s.headers)).status_code == 403
    r = await client.post(
        f"/api/v1/admin/profiles/{pid}/decision", json={"decision": "approve"}, headers=s.headers
    )
    assert r.status_code == 403


async def test_queue_and_review_detail(client: AsyncClient) -> None:
    mod = await moderator(client)
    _, pid, _ = await _submitted(client)
    q = (await client.get("/api/v1/admin/profiles", headers=mod.headers)).json()
    assert q["total"] == 1 and q["items"][0]["id"] == pid and q["items"][0]["pending_photos"] == 1
    d = (await client.get(f"/api/v1/admin/profiles/{pid}", headers=mod.headers)).json()
    assert d["owner_phone_masked"] == "+91******3210"
    assert d["profile"]["my_role"] == "staff"
    assert d["history"][0]["to_status"] == "submitted"
    logs = await client.get("/api/v1/admin/audit-logs?action=moderation.view", headers=mod.headers)
    assert logs.status_code == 403  # moderators can't read the audit log (ops/super admin only)


async def test_approve_requires_an_approved_photo(client: AsyncClient) -> None:
    mod = await moderator(client)
    s, pid, photos = await _submitted(client)
    r = await client.post(
        f"/api/v1/admin/profiles/{pid}/decision", json={"decision": "approve"}, headers=mod.headers
    )
    assert r.json()["error"]["code"] == "no_approved_photo"
    r = await client.post(
        f"/api/v1/admin/profiles/{pid}/decision",
        json={"decision": "approve", "photos": {photos[0]["id"]: "approve"}},
        headers=mod.headers,
    )
    assert r.status_code == 200
    me = (await client.get(f"/api/v1/profiles/{pid}", headers=s.headers)).json()
    assert me["status"] == "approved" and me["approved_at"]
    assert me["photos"][0]["moderation_status"] == "approved"


async def test_request_changes_then_resubmit(client: AsyncClient) -> None:
    mod = await moderator(client)
    s, pid, _ = await _submitted(client)
    r = await client.post(
        f"/api/v1/admin/profiles/{pid}/decision",
        json={"decision": "request_changes"},
        headers=mod.headers,
    )
    assert r.json()["error"]["code"] == "reason_required"
    r = await client.post(
        f"/api/v1/admin/profiles/{pid}/decision",
        json={
            "decision": "request_changes",
            "reason_code": "contact_in_text",
            "note": "Please remove the phone number.",
        },
        headers=mod.headers,
    )
    assert r.status_code == 200
    me = (await client.get(f"/api/v1/profiles/{pid}", headers=s.headers)).json()
    assert me["status"] == "needs_changes"
    assert me["status_reason_code"] == "contact_in_text"
    assert me["status_note"] == "Please remove the phone number."
    r = await client.post(f"/api/v1/profiles/{pid}/submit", headers=s.headers)
    assert r.json()["status"] == "submitted"


async def test_moderator_cannot_review_own_profile(client: AsyncClient) -> None:
    mod = await moderator(client)
    pid = (await create_profile(client, mod))["id"]
    await complete_profile(client, mod, pid)
    await client.post(f"/api/v1/profiles/{pid}/submit", headers=mod.headers)
    r = await client.post(
        f"/api/v1/admin/profiles/{pid}/decision", json={"decision": "approve"}, headers=mod.headers
    )
    assert r.json()["error"]["code"] == "conflict_of_interest"
    assert MODERATOR_PHONE  # documented in helpers


# ------------------------------------------------------------------ family delegation


async def _parent_creates(client: AsyncClient) -> tuple[object, str]:
    parent = await login(client, PARENT)
    r = await client.post(
        "/api/v1/profiles",
        json={
            "created_for": "daughter",
            "subject_name": "Kavya",
            "subject_phone": "98222 22222",
            "gender": "female",
        },
        headers=parent.headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["my_role"] == "creator_pending" and r.json()["subject_consent_pending"]
    return parent, r.json()["id"]


async def test_family_member_cannot_edit_before_consent(client: AsyncClient) -> None:
    parent, pid = await _parent_creates(client)
    r = await put(client, parent, pid, "basic", BASIC)
    assert r.status_code == 409 and r.json()["error"]["code"] == "subject_consent_pending"
    r = await upload_photo(client, parent, pid)
    assert r.json()["error"]["code"] == "subject_consent_pending"
    r = await client.post(f"/api/v1/profiles/{pid}/submit", headers=parent.headers)
    assert r.json()["error"]["code"] == "subject_consent_pending"


async def test_subject_accepts_and_chooses_scope(client: AsyncClient) -> None:
    parent, pid = await _parent_creates(client)
    daughter = await login(client, DAUGHTER)
    invites = (await client.get("/api/v1/delegations/invitations", headers=daughter.headers)).json()
    assert len(invites) == 1 and invites[0]["kind"] == "subject_consent"
    assert invites[0]["subject_name"] == "Kavya"
    assert invites[0]["invited_by_phone_masked"] == "+91******1111"
    r = await client.post(
        f"/api/v1/delegations/{invites[0]['id']}/accept",
        json={"scopes": ["edit_profile"]},
        headers=daughter.headers,
    )
    assert r.json()["profile_id"] == pid

    mine = (await client.get(f"/api/v1/profiles/{pid}", headers=daughter.headers)).json()
    assert mine["my_role"] == "owner" and not mine["subject_consent_pending"]
    parents = (await client.get(f"/api/v1/profiles/{pid}", headers=parent.headers)).json()
    assert parents["my_role"] == "delegate" and parents["my_scopes"] == ["edit_profile"]

    assert (await put(client, parent, pid, "basic", BASIC)).status_code == 200
    r = await upload_photo(client, parent, pid)
    assert r.status_code == 403 and r.json()["error"]["code"] == "delegation_scope"
    r = await client.post(f"/api/v1/profiles/{pid}/pause", headers=parent.headers)
    assert r.json()["error"]["code"] == "owner_only"

    delegates = (
        await client.get(f"/api/v1/profiles/{pid}/delegates", headers=daughter.headers)
    ).json()
    assert len(delegates) == 1
    r = await client.delete(f"/api/v1/delegates/{delegates[0]['id']}", headers=daughter.headers)
    assert r.status_code == 204
    assert (await client.get(f"/api/v1/profiles/{pid}", headers=parent.headers)).status_code == 404


async def test_subject_declines_and_draft_is_closed(client: AsyncClient) -> None:
    parent, pid = await _parent_creates(client)
    daughter = await login(client, DAUGHTER)
    invite = (await client.get("/api/v1/delegations/invitations", headers=daughter.headers)).json()[
        0
    ]
    r = await client.post(f"/api/v1/delegations/{invite['id']}/decline", headers=daughter.headers)
    assert r.status_code == 204
    assert (await client.get("/api/v1/profiles/managed", headers=parent.headers)).json() == []
    assert (await client.get(f"/api/v1/profiles/{pid}", headers=parent.headers)).status_code == 404


async def test_only_the_invited_phone_can_accept(client: AsyncClient) -> None:
    _, _ = await _parent_creates(client)
    daughter = await login(client, DAUGHTER)
    invite = (await client.get("/api/v1/delegations/invitations", headers=daughter.headers)).json()[
        0
    ]
    intruder = await login(client, A)
    assert (
        await client.get("/api/v1/delegations/invitations", headers=intruder.headers)
    ).json() == []
    r = await client.post(
        f"/api/v1/delegations/{invite['id']}/accept", json={}, headers=intruder.headers
    )
    assert r.status_code == 404


async def test_subject_with_existing_profile_cannot_accept(client: AsyncClient) -> None:
    _, _ = await _parent_creates(client)
    daughter = await login(client, DAUGHTER)
    await create_profile(client, daughter, subject_name="Kavya")
    invite = (await client.get("/api/v1/delegations/invitations", headers=daughter.headers)).json()[
        0
    ]
    r = await client.post(
        f"/api/v1/delegations/{invite['id']}/accept", json={}, headers=daughter.headers
    )
    assert r.json()["error"]["code"] == "profile_exists"


async def test_owner_invites_helper_who_can_be_revoked(client: AsyncClient) -> None:
    owner = await login(client, A)
    pid = (await create_profile(client, owner))["id"]
    r = await client.post(
        f"/api/v1/profiles/{pid}/delegates",
        json={"phone": MOTHER, "relationship": "relative", "scopes": ["manage_photos"]},
        headers=owner.headers,
    )
    assert r.status_code == 201
    mother = await login(client, MOTHER)
    invite = (await client.get("/api/v1/delegations/invitations", headers=mother.headers)).json()[0]
    assert invite["kind"] == "helper_invite"
    await client.post(f"/api/v1/delegations/{invite['id']}/accept", json={}, headers=mother.headers)
    managed = (await client.get("/api/v1/profiles/managed", headers=mother.headers)).json()
    assert managed[0]["id"] == pid and managed[0]["my_role"] == "delegate"
    assert (await upload_photo(client, mother, pid)).status_code == 201
    assert (await put(client, mother, pid, "basic", BASIC)).status_code == 403

    # Helpers cannot invite more helpers.
    r = await client.post(
        f"/api/v1/profiles/{pid}/delegates",
        json={"phone": "+919844444444", "relationship": "relative", "scopes": []},
        headers=mother.headers,
    )
    assert r.json()["error"]["code"] == "owner_only"
    # A helper can leave on their own.
    mine = (await client.get(f"/api/v1/profiles/{pid}/delegates", headers=mother.headers)).json()
    me = next(d for d in mine if d["is_me"])
    assert (
        await client.delete(f"/api/v1/delegates/{me['id']}", headers=mother.headers)
    ).status_code == 204
    assert (await client.get(f"/api/v1/profiles/{pid}", headers=mother.headers)).status_code == 404


async def test_cannot_create_profile_for_own_number(client: AsyncClient) -> None:
    s = await login(client, A)
    r = await client.post(
        "/api/v1/profiles",
        json={"created_for": "son", "subject_name": "Me", "subject_phone": A},
        headers=s.headers,
    )
    assert r.json()["error"]["code"] == "invalid_invitee"
    r = await client.post(
        "/api/v1/profiles",
        json={"created_for": "son", "subject_name": "No phone"},
        headers=s.headers,
    )
    assert r.json()["error"]["code"] == "subject_phone_required"
    assert grant_role  # imported for parity with other suites


# ------------------------------------------------------------------ preferences


async def test_partner_preferences(client: AsyncClient) -> None:
    s = await login(client, A)
    other = await login(client, PARENT)
    pid = (await create_profile(client, s))["id"]
    url = f"/api/v1/profiles/{pid}/preferences"
    bad = [
        {"age_min": 30, "age_max": 25},
        {"age_min": 16},
        {"must_have": ["age"], "preferred": ["age"]},
        {"district_codes": ["tn-nowhere"]},
        {"marital_statuses": ["single"]},
    ]
    for body in bad:
        assert (await client.post(url, json=body, headers=s.headers)).status_code == 422, body

    body = {
        "age_min": 26,
        "age_max": 32,
        "height_min_cm": 165,
        "marital_statuses": ["never_married"],
        "district_codes": ["tn-chennai", "tn-coimbatore"],
        "sub_community_codes": ["sub_a"],
        "must_have": ["age", "marital_status"],
        "preferred": ["location"],
    }
    r = await client.post(url, json=body, headers=s.headers)
    assert r.status_code == 201, r.text
    pref = r.json()
    assert pref["is_default"] and pref["sub_community_codes"] == ["sub_a"]
    assert "education" in pref["flexible"] and "age" not in pref["flexible"]
    me = (await client.get(f"/api/v1/profiles/{pid}", headers=s.headers)).json()
    assert me["completion"]["sections"]["preferences"] is True

    r = await client.put(
        f"/api/v1/preferences/{pref['id']}", json={**body, "age_max": 35}, headers=s.headers
    )
    assert r.json()["age_max"] == 35
    assert (
        await client.put(f"/api/v1/preferences/{pref['id']}", json=body, headers=other.headers)
    ).status_code == 404
    assert (await client.get(url, headers=other.headers)).status_code == 404
    assert (
        await client.delete(f"/api/v1/preferences/{pref['id']}", headers=s.headers)
    ).status_code == 204
    assert (await client.get(url, headers=s.headers)).json() == []
