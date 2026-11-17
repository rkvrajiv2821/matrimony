"""Shared helpers for profile, photo, delegation and moderation tests."""

import io
from datetime import date
from typing import Any

import httpx
from httpx import AsyncClient
from PIL import Image

from tests.conftest import LoggedIn, grant_role, login

MODERATOR_PHONE = "+919000000009"

BASIC: dict[str, Any] = {
    "subject_name": "Priya Sundaram",
    "display_name": "Priya S.",
    "date_of_birth": "1998-04-12",
    "gender": "female",
    "marital_status": "never_married",
    "height_cm": 162,
    "mother_tongue": "tamil",
    "current_country": "IN",
    "state_code": "in-tn",
    "district_code": "tn-chennai",
    "city_code": "tn-chennai-city",
}
EDUCATION = {
    "qualification": "masters",
    "field_of_study": "engineering",
    "institution": "Anna University",
}
CAREER = {
    "employment_type": "private",
    "occupation": "Software engineer",
    "industry": "it_software",
    "employer": "Acme Pvt Ltd",
    "income_band": "10_20l",
    "visibility": "members",
}


def jpeg(width: int = 800, height: int = 1000, *, exif_gps: bool = False) -> bytes:
    img = Image.new("RGB", (width, height), (180, 40, 60))
    out = io.BytesIO()
    if exif_gps:
        exif = Image.Exif()
        exif[0x010F] = "SecretPhoneMaker"  # Make
        exif[0x8825] = {1: "N", 2: (13.0, 4.0, 0.0)}  # GPSInfo
        img.save(out, format="JPEG", exif=exif)
    else:
        img.save(out, format="JPEG")
    return out.getvalue()


def png(width: int = 800, height: int = 800) -> bytes:
    out = io.BytesIO()
    Image.new("RGBA", (width, height), (0, 0, 0, 0)).save(out, format="PNG")
    return out.getvalue()


async def create_profile(client: AsyncClient, s: LoggedIn, **body: Any) -> dict[str, Any]:
    payload = {"created_for": "self", "subject_name": "Priya Sundaram", **body}
    r = await client.post("/api/v1/profiles", json=payload, headers=s.headers)
    assert r.status_code == 201, r.text
    return dict(r.json())


async def put(
    client: AsyncClient, s: LoggedIn, pid: str, section: str, body: dict[str, Any]
) -> httpx.Response:
    return await client.put(f"/api/v1/profiles/{pid}/{section}", json=body, headers=s.headers)


async def upload_photo(
    client: AsyncClient,
    s: LoggedIn,
    pid: str,
    data: bytes | None = None,
    content_type: str = "image/jpeg",
    visibility: str = "members",
) -> httpx.Response:
    data = data if data is not None else jpeg()
    r = await client.post(
        f"/api/v1/profiles/{pid}/photos/upload-url",
        json={"content_type": content_type, "size_bytes": len(data)},
        headers=s.headers,
    )
    if r.status_code != 201:
        return r
    up = r.json()
    async with httpx.AsyncClient() as s3:
        res = await s3.post(up["url"], data=up["fields"], files={"file": ("p", data, content_type)})
        assert res.status_code in (200, 204), res.text
    return await client.post(
        f"/api/v1/profiles/{pid}/photos",
        json={"upload_id": up["upload_id"], "visibility": visibility},
        headers=s.headers,
    )


async def complete_profile(client: AsyncClient, s: LoggedIn, pid: str, **basic: Any) -> None:
    for section, body in (
        ("basic", {**BASIC, **basic}),
        ("education", EDUCATION),
        ("career", CAREER),
    ):
        r = await put(client, s, pid, section, body)
        assert r.status_code == 200, r.text
    r = await upload_photo(client, s, pid)
    assert r.status_code == 201, r.text


async def moderator(client: AsyncClient) -> LoggedIn:
    await login(client, MODERATOR_PHONE)
    await grant_role(MODERATOR_PHONE, "moderator")
    return await login(client, MODERATOR_PHONE)


async def approved_member(
    client: AsyncClient, phone: str, mod: LoggedIn, **basic: Any
) -> tuple[LoggedIn, str]:
    """Register, complete, submit and approve a profile; returns (session, profile_id)."""
    s = await login(client, phone)
    pid = (await create_profile(client, s, subject_name=basic.get("subject_name", "Member")))["id"]
    await complete_profile(client, s, pid, **basic)
    r = await client.post(f"/api/v1/profiles/{pid}/submit", headers=s.headers)
    assert r.status_code == 200, r.text
    photos = r.json()["photos"]
    r = await client.post(
        f"/api/v1/admin/profiles/{pid}/decision",
        json={"decision": "approve", "photos": {p["id"]: "approve" for p in photos}},
        headers=mod.headers,
    )
    assert r.status_code == 200, r.text
    return s, pid


def adult_dob(years: int) -> str:
    today = date.today()
    return date(today.year - years, today.month, min(today.day, 28)).isoformat()
