from httpx import AsyncClient

from tests.conftest import login
from tests.profile_helpers import (
    BASIC,
    CAREER,
    EDUCATION,
    adult_dob,
    approved_member,
    complete_profile,
    create_profile,
    moderator,
    put,
)

A = "+919876543210"
B = "+919812345678"


async def test_reference_data(client: AsyncClient) -> None:
    opts = (await client.get("/api/v1/reference/options")).json()
    assert "never_married" in opts["options"]["marital_status"]
    assert opts["min_age"] == 18
    tn = (await client.get("/api/v1/reference/locations?parent=in-tn")).json()
    assert len(tn) == 38 and all(d["type"] == "district" for d in tn)
    chennai = next(d for d in tn if d["code"] == "tn-chennai")
    assert chennai["name_ta"] == "சென்னை"
    cities = (await client.get("/api/v1/reference/locations?parent=tn-krishnagiri")).json()
    assert {c["code"] for c in cities} == {"tn-krishnagiri-city", "tn-hosur"}
    community = (await client.get("/api/v1/reference/community")).json()
    assert community[0]["code"] == "launch_community"
    assert "placeholder" in community[0]["label_en"].lower()


async def test_create_self_profile_once(client: AsyncClient) -> None:
    s = await login(client, A)
    p = await create_profile(client, s)
    assert p["my_role"] == "owner" and p["status"] == "draft"
    assert p["community_label"]["code"] == "launch_community"
    assert p["completion"]["missing_required"] == [
        "basic",
        "location",
        "education",
        "career",
        "photo",
    ]
    r = await client.post(
        "/api/v1/profiles", json={"created_for": "self", "subject_name": "Again"}, headers=s.headers
    )
    assert r.json()["error"]["code"] == "profile_exists"
    managed = (await client.get("/api/v1/profiles/managed", headers=s.headers)).json()
    assert [m["id"] for m in managed] == [p["id"]]


async def test_sections_save_and_completion(client: AsyncClient) -> None:
    s = await login(client, A)
    pid = (await create_profile(client, s))["id"]
    r = await put(client, s, pid, "basic", BASIC)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["age"] >= 18 and body["district"]["code"] == "tn-chennai"
    assert body["completion"]["sections"]["basic"] is True
    await put(client, s, pid, "education", EDUCATION)
    r = await put(client, s, pid, "career", CAREER)
    assert r.json()["completion"]["missing_required"] == ["photo"]
    r = await put(
        client,
        s,
        pid,
        "lifestyle",
        {
            "diet": "vegetarian",
            "languages": ["tamil", "english", "tamil"],
            "about_me": "I love music.",
        },
    )
    assert r.json()["lifestyle"]["languages"] == ["tamil", "english"]
    r = await put(client, s, pid, "community", {"sub_community_code": "sub_b"})
    assert r.json()["community"]["sub_community_code"] == "sub_b"
    r = await put(client, s, pid, "community", {"sub_community_code": "not-a-code"})
    assert r.status_code == 422


async def test_age_limits(client: AsyncClient) -> None:
    s = await login(client, A)
    pid = (await create_profile(client, s))["id"]
    r = await put(client, s, pid, "basic", {**BASIC, "date_of_birth": adult_dob(17)})
    assert r.status_code == 422 and r.json()["error"]["code"] == "underage"
    r = await put(client, s, pid, "basic", {**BASIC, "date_of_birth": adult_dob(85)})
    assert r.status_code == 422
    r = await put(client, s, pid, "basic", {**BASIC, "date_of_birth": adult_dob(18)})
    assert r.status_code == 200


async def test_location_hierarchy_is_enforced(client: AsyncClient) -> None:
    s = await login(client, A)
    pid = (await create_profile(client, s))["id"]
    bad = [
        {"district_code": "tn-madurai", "city_code": "tn-chennai-city"},  # city not in district
        {"state_code": "in-kerala", "district_code": "tn-chennai", "city_code": None},
        {"current_country": "SG", "state_code": "in-tn"},  # state not in country
        {"state_code": None, "district_code": "tn-chennai", "city_code": None},
        {"current_country": "XX", "state_code": None, "district_code": None, "city_code": None},
    ]
    for override in bad:
        r = await put(client, s, pid, "basic", {**BASIC, **override})
        assert r.status_code == 422, override
    r = await put(
        client,
        s,
        pid,
        "basic",
        {
            **BASIC,
            "current_country": "SG",
            "state_code": None,
            "district_code": None,
            "city_code": None,
        },
    )
    assert r.status_code == 200
    assert r.json()["completion"]["sections"]["location"] is True


async def test_contact_details_rejected_in_free_text(client: AsyncClient) -> None:
    s = await login(client, A)
    pid = (await create_profile(client, s))["id"]
    for text in [
        "Call me on 98765 43210",
        "mail priya@example.com",
        "see wa.me/919876543210",
        "priya [at] gmail (dot) com",
    ]:
        r = await put(client, s, pid, "lifestyle", {"about_me": text})
        assert r.status_code == 422, text
        assert r.json()["error"]["code"] == "contact_details_not_allowed"
    r = await put(client, s, pid, "lifestyle", {"about_me": "B.E. 2012-2016, born in 1994."})
    assert r.status_code == 200
    r = await put(client, s, pid, "basic", {**BASIC, "display_name": "Priya 9876543210"})
    assert r.json()["error"]["code"] == "contact_details_not_allowed"


async def test_submit_requires_completion(client: AsyncClient) -> None:
    s = await login(client, A)
    pid = (await create_profile(client, s))["id"]
    await put(client, s, pid, "basic", BASIC)
    r = await client.post(f"/api/v1/profiles/{pid}/submit", headers=s.headers)
    assert r.status_code == 422
    assert r.json()["error"]["details"]["missing"] == ["education", "career", "photo"]
    await complete_profile(client, s, pid)
    r = await client.post(f"/api/v1/profiles/{pid}/submit", headers=s.headers)
    assert r.status_code == 200 and r.json()["status"] == "submitted"
    r = await client.post(f"/api/v1/profiles/{pid}/submit", headers=s.headers)
    assert r.json()["error"]["code"] == "invalid_transition"


async def test_other_members_cannot_read_or_change_a_profile(client: AsyncClient) -> None:
    a = await login(client, A)
    b = await login(client, B)
    pid = (await create_profile(client, a))["id"]
    assert (await client.get(f"/api/v1/profiles/{pid}", headers=b.headers)).status_code == 404
    assert (
        await client.get(f"/api/v1/profiles/{pid}/preview", headers=b.headers)
    ).status_code == 404
    assert (await put(client, b, pid, "basic", BASIC)).status_code == 404
    assert (
        await client.post(f"/api/v1/profiles/{pid}/submit", headers=b.headers)
    ).status_code == 404
    assert (
        await client.post(f"/api/v1/profiles/{pid}/pause", headers=b.headers)
    ).status_code == 404


async def test_member_view_hides_private_fields(client: AsyncClient) -> None:
    mod = await moderator(client)
    a, pid_a = await approved_member(client, A, mod, subject_name="Priya Sundaram")
    b, _ = await approved_member(client, B, mod, subject_name="Arun Kumar", gender="male")

    # Hide employer and income from members.
    await put(client, a, pid_a, "career", {**CAREER, "visibility": "connections"})
    view = (await client.get(f"/api/v1/profiles/{pid_a}", headers=b.headers)).json()
    assert view["display_name"] == "Priya S."
    assert "date_of_birth" not in view and "subject_name" not in view
    assert view["age"] >= 18
    assert view["occupation"] == "Software engineer"
    assert view["employer"] is None and view["income_band"] is None
    assert len(view["photos"]) == 1
    serialized = str(view)
    assert "Sundaram" not in serialized and "+91" not in serialized and "1998" not in serialized


async def test_unapproved_viewer_cannot_see_others(client: AsyncClient) -> None:
    mod = await moderator(client)
    _, pid_a = await approved_member(client, A, mod)
    b = await login(client, B)
    await create_profile(client, b)  # draft only
    assert (await client.get(f"/api/v1/profiles/{pid_a}", headers=b.headers)).status_code == 404


async def test_material_change_triggers_re_review(client: AsyncClient) -> None:
    mod = await moderator(client)
    a, pid = await approved_member(client, A, mod)
    r = await put(client, a, pid, "basic", {**BASIC, "height_cm": 165})
    assert r.json()["status"] == "approved"  # non-material
    r = await put(client, a, pid, "lifestyle", {"about_me": "Updated introduction."})
    assert r.json()["status"] == "submitted"
    assert r.json()["status_reason_code"] == "material_change"


async def test_pause_hides_profile(client: AsyncClient) -> None:
    mod = await moderator(client)
    a, pid_a = await approved_member(client, A, mod)
    b, _ = await approved_member(client, B, mod, gender="male")
    assert (await client.get(f"/api/v1/profiles/{pid_a}", headers=b.headers)).status_code == 200
    r = await client.post(f"/api/v1/profiles/{pid_a}/pause", headers=a.headers)
    assert r.json()["visibility"] == "paused"
    assert (await client.get(f"/api/v1/profiles/{pid_a}", headers=b.headers)).status_code == 404
    await client.post(f"/api/v1/profiles/{pid_a}/resume", headers=a.headers)
    assert (await client.get(f"/api/v1/profiles/{pid_a}", headers=b.headers)).status_code == 200
