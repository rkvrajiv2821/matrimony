import io

from httpx import AsyncClient
from PIL import Image

from app.common.config import get_settings
from app.media import storage
from tests.conftest import login
from tests.profile_helpers import (
    approved_member,
    complete_profile,
    create_profile,
    jpeg,
    moderator,
    png,
    upload_photo,
)

A = "+919876543210"
B = "+919812345678"


async def _list_keys() -> list[str]:
    import anyio

    def run() -> list[str]:
        resp = storage._client().list_objects_v2(Bucket=get_settings().storage_bucket)
        return [o["Key"] for o in resp.get("Contents", [])]

    return await anyio.to_thread.run_sync(run)


async def test_upload_is_re_encoded_and_metadata_stripped(client: AsyncClient) -> None:
    s = await login(client, A)
    pid = (await create_profile(client, s))["id"]
    r = await upload_photo(client, s, pid, jpeg(3000, 2000, exif_gps=True))
    assert r.status_code == 201, r.text
    photo = r.json()
    assert photo["is_primary"] is True and photo["moderation_status"] == "pending"
    assert max(photo["width"], photo["height"]) == 1600

    r = await client.get(photo["full_url"], headers=s.headers)
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert r.headers["cache-control"].startswith("private")
    with Image.open(io.BytesIO(r.content)) as img:
        assert dict(img.getexif()) == {}
    thumb = await client.get(photo["thumb_url"], headers=s.headers)
    with Image.open(io.BytesIO(thumb.content)) as img:
        assert max(img.size) == 480

    keys = await _list_keys()
    assert not any(k.startswith("uploads/") for k in keys), "original upload must be deleted"


async def test_png_with_transparency_is_flattened(client: AsyncClient) -> None:
    s = await login(client, A)
    pid = (await create_profile(client, s))["id"]
    r = await upload_photo(client, s, pid, png(), content_type="image/png")
    assert r.status_code == 201, r.text


async def test_rejects_non_images_mismatches_and_tiny_photos(client: AsyncClient) -> None:
    s = await login(client, A)
    pid = (await create_profile(client, s))["id"]
    r = await upload_photo(client, s, pid, b"<?php system($_GET['x']); ?>" * 10)
    assert r.json()["error"]["code"] == "invalid_image"
    r = await upload_photo(client, s, pid, png(), content_type="image/jpeg")
    assert r.json()["error"]["code"] == "invalid_image"
    r = await upload_photo(client, s, pid, jpeg(200, 200))
    assert r.json()["error"]["code"] == "image_too_small"
    r = await client.post(
        f"/api/v1/profiles/{pid}/photos/upload-url",
        json={"content_type": "image/gif", "size_bytes": 10},
        headers=s.headers,
    )
    assert r.status_code == 422
    r = await client.post(
        f"/api/v1/profiles/{pid}/photos/upload-url",
        json={"content_type": "image/jpeg", "size_bytes": 50 * 1024 * 1024},
        headers=s.headers,
    )
    assert r.json()["error"]["code"] == "image_too_large"
    assert not any(k.startswith("uploads/") for k in await _list_keys())


async def test_upload_id_is_bound_to_profile_and_single_use(client: AsyncClient) -> None:
    a = await login(client, A)
    b = await login(client, B)
    pid_a = (await create_profile(client, a))["id"]
    pid_b = (await create_profile(client, b))["id"]
    r = await client.post(
        f"/api/v1/profiles/{pid_a}/photos/upload-url",
        json={"content_type": "image/jpeg", "size_bytes": 1000},
        headers=a.headers,
    )
    upload_id = r.json()["upload_id"]
    r = await client.post(
        f"/api/v1/profiles/{pid_b}/photos", json={"upload_id": upload_id}, headers=b.headers
    )
    assert r.status_code == 404
    r = await client.post(
        f"/api/v1/profiles/{pid_a}/photos", json={"upload_id": upload_id}, headers=a.headers
    )
    assert r.status_code == 404  # consumed by the attempt above, and never uploaded anyway


async def test_photo_limit_and_primary_promotion(client: AsyncClient) -> None:
    s = await login(client, A)
    pid = (await create_profile(client, s))["id"]
    ids = []
    for _ in range(6):
        r = await upload_photo(client, s, pid)
        assert r.status_code == 201, r.text
        ids.append(r.json()["id"])
    r = await upload_photo(client, s, pid)
    assert r.json()["error"]["code"] == "too_many_photos"

    r = await client.patch(
        f"/api/v1/profiles/{pid}/photos/{ids[2]}", json={"is_primary": True}, headers=s.headers
    )
    assert r.json()["is_primary"] is True
    r = await client.delete(f"/api/v1/profiles/{pid}/photos/{ids[2]}", headers=s.headers)
    assert r.status_code == 204
    photos = (await client.get(f"/api/v1/profiles/{pid}", headers=s.headers)).json()["photos"]
    assert len(photos) == 5 and sum(p["is_primary"] for p in photos) == 1


async def test_photo_visibility_rules(client: AsyncClient) -> None:
    mod = await moderator(client)
    a, pid_a = await approved_member(client, A, mod)
    b, _ = await approved_member(client, B, mod, gender="male")
    stranger = await login(client, "+919811111111")

    approved = (await client.get(f"/api/v1/profiles/{pid_a}", headers=a.headers)).json()["photos"][
        0
    ]
    assert (await client.get(approved["thumb_url"], headers=b.headers)).status_code == 200
    # A member without an approved profile can't browse photos.
    assert (await client.get(approved["thumb_url"], headers=stranger.headers)).status_code == 404

    pending = (await upload_photo(client, a, pid_a)).json()
    assert (await client.get(pending["thumb_url"], headers=a.headers)).status_code == 200
    assert (await client.get(pending["thumb_url"], headers=b.headers)).status_code == 404
    assert (await client.get(pending["thumb_url"], headers=mod.headers)).status_code == 200

    private = (await upload_photo(client, a, pid_a, visibility="connections")).json()
    await client.post(
        f"/api/v1/admin/photos/{private['id']}/decision",
        json={"decision": "approve"},
        headers=mod.headers,
    )
    assert (await client.get(private["thumb_url"], headers=b.headers)).status_code == 404
    view = (await client.get(f"/api/v1/profiles/{pid_a}", headers=b.headers)).json()
    assert [p["id"] for p in view["photos"]] == [approved["id"]]


async def test_rejected_photo_does_not_count_and_loses_primary(client: AsyncClient) -> None:
    mod = await moderator(client)
    s = await login(client, A)
    pid = (await create_profile(client, s))["id"]
    await complete_profile(client, s, pid)
    first = (await client.get(f"/api/v1/profiles/{pid}", headers=s.headers)).json()["photos"][0]
    second = (await upload_photo(client, s, pid)).json()
    r = await client.post(
        f"/api/v1/admin/photos/{first['id']}/decision",
        json={"decision": "reject", "reason_code": "photo_unclear"},
        headers=mod.headers,
    )
    assert r.status_code == 204
    photos = {
        p["id"]: p
        for p in (await client.get(f"/api/v1/profiles/{pid}", headers=s.headers)).json()["photos"]
    }
    assert photos[first["id"]]["moderation_status"] == "rejected"
    assert photos[first["id"]]["moderation_reason"] == "photo_unclear"
    assert photos[second["id"]]["is_primary"] is True
