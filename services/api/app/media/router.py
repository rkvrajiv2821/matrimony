"""Profile photos: presigned upload → validation → private storage → authorised reads."""

import json
import uuid
from typing import Annotated, Literal

import anyio
from fastapi import APIRouter, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.audit import service as audit
from app.common.config import get_settings
from app.common.errors import AppError, Conflict, NotFound
from app.common.ids import uuid7
from app.common.redis import get_redis
from app.common.time import utcnow
from app.delegation.models import Scope
from app.media import images, storage
from app.media.models import ProfilePhoto
from app.profiles import service as profiles
from app.profiles.access import load_managed, role_for
from app.profiles.models import Profile
from app.profiles.options import ModerationStatus, Visibility
from app.profiles.schemas import PhotoOut
from app.security.deps import DB, Auth, Meta
from app.security.roles import RoleCode

router = APIRouter(tags=["media"])

STAFF_ROLES = {
    RoleCode.SUPER_ADMIN,
    RoleCode.OPERATIONS_ADMIN,
    RoleCode.MODERATOR,
    RoleCode.VERIFICATION_OPERATOR,
}


class UploadUrlIn(BaseModel):
    content_type: Literal["image/jpeg", "image/png", "image/webp"]
    size_bytes: int = Field(gt=0)


class UploadUrlOut(BaseModel):
    upload_id: str
    url: str
    fields: dict[str, str]
    expires_in: int
    max_bytes: int


class PhotoConfirmIn(BaseModel):
    upload_id: str = Field(max_length=64)
    visibility: Visibility = Visibility.MEMBERS


class PhotoPatchIn(BaseModel):
    is_primary: Literal[True] | None = None
    visibility: Visibility | None = None
    sort_order: int | None = Field(default=None, ge=0, le=20)


def _upload_key(upload_id: str) -> str:
    return f"upload:{upload_id}"


async def _photo_count(db: DB, profile_id: int) -> int:
    return int(
        await db.scalar(
            select(func.count())
            .select_from(ProfilePhoto)
            .where(ProfilePhoto.profile_id == profile_id, ProfilePhoto.deleted_at.is_(None))
        )
        or 0
    )


@router.post(
    "/profiles/{profile_id}/photos/upload-url",
    response_model=UploadUrlOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_url(profile_id: uuid.UUID, body: UploadUrlIn, auth: Auth, db: DB) -> UploadUrlOut:
    s = get_settings()
    managed = await load_managed(db, auth.user, profile_id)
    managed.require(Scope.MANAGE_PHOTOS)
    managed.require_editable()
    if body.size_bytes > s.photo_max_bytes:
        raise AppError(
            "This photo is too large (max 8 MB).", code="image_too_large", status_code=422
        )
    if await _photo_count(db, managed.profile.id) >= s.photo_max_count:
        raise Conflict("You can add up to 6 photos.", code="too_many_photos")

    upload_id = str(uuid7())
    key = f"uploads/{managed.profile.public_id}/{upload_id}"
    post = await storage.presign_post(
        key, body.content_type, s.photo_max_bytes, s.upload_url_ttl_seconds
    )
    await get_redis().set(
        _upload_key(upload_id),
        json.dumps(
            {
                "profile_id": managed.profile.id,
                "user_id": auth.user.id,
                "key": key,
                "content_type": body.content_type,
            }
        ),
        ex=s.upload_url_ttl_seconds + 60,
    )
    return UploadUrlOut(
        upload_id=upload_id,
        url=post.url,
        fields=post.fields,
        expires_in=s.upload_url_ttl_seconds,
        max_bytes=s.photo_max_bytes,
    )


@router.post(
    "/profiles/{profile_id}/photos", response_model=PhotoOut, status_code=status.HTTP_201_CREATED
)
async def confirm_photo(
    profile_id: uuid.UUID, body: PhotoConfirmIn, auth: Auth, db: DB, meta: Meta
) -> PhotoOut:
    s = get_settings()
    managed = await load_managed(db, auth.user, profile_id, for_update=True)
    managed.require(Scope.MANAGE_PHOTOS)
    managed.require_editable()
    profile = managed.profile

    raw = await get_redis().getdel(_upload_key(body.upload_id))  # single use
    pending = json.loads(str(raw)) if raw else None
    if not pending or pending["profile_id"] != profile.id or pending["user_id"] != auth.user.id:
        raise NotFound("Upload not found or expired.")
    key: str = pending["key"]
    try:
        size = await storage.size_of(key)
        if size is None:
            raise AppError("The upload did not complete.", code="upload_missing", status_code=422)
        if size > s.photo_max_bytes:
            raise AppError(
                "This photo is too large (max 8 MB).", code="image_too_large", status_code=422
            )
        if await _photo_count(db, profile.id) >= s.photo_max_count:
            raise Conflict("You can add up to 6 photos.", code="too_many_photos")
        data = await storage.get_bytes(key)
        if data is None:
            raise AppError("The upload did not complete.", code="upload_missing", status_code=422)
        processed = await anyio.to_thread.run_sync(images.process, data, pending["content_type"])
    finally:
        await storage.delete(key)  # the unprocessed original is never kept

    photo_id = uuid7()
    base = f"profiles/{profile.public_id}/photos/{photo_id}"
    await storage.put_bytes(f"{base}/full.jpg", processed.full, "image/jpeg")
    await storage.put_bytes(f"{base}/thumb.jpg", processed.thumb, "image/jpeg")
    is_first = await _photo_count(db, profile.id) == 0
    photo = ProfilePhoto(
        public_id=photo_id,
        profile_id=profile.id,
        storage_key=f"{base}/full.jpg",
        thumbnail_key=f"{base}/thumb.jpg",
        width=processed.width,
        height=processed.height,
        is_primary=is_first,
        sort_order=await _photo_count(db, profile.id),
        visibility=body.visibility.value,
        moderation_status=ModerationStatus.PENDING,
        uploaded_by_user_id=auth.user.id,
    )
    db.add(photo)
    await db.flush()
    await audit.record(
        db,
        action="photo.upload",
        resource_type="profile_photo",
        resource_id=str(photo.public_id),
        actor_user_id=auth.user.id,
        after={"profile": str(profile.public_id), "visibility": photo.visibility},
        ip_hash=meta.ip_hash,
        request_id=meta.request_id,
    )
    await profiles.refresh_completion(db, profile)
    return profiles.photo_out(photo)


async def _managed_photo(
    db: DB, auth: Auth, profile_id: uuid.UUID, photo_id: uuid.UUID
) -> tuple[ProfilePhoto, Profile]:
    managed = await load_managed(db, auth.user, profile_id, for_update=True)
    managed.require(Scope.MANAGE_PHOTOS)
    managed.require_editable()
    photo = await db.scalar(
        select(ProfilePhoto).where(
            ProfilePhoto.public_id == photo_id,
            ProfilePhoto.profile_id == managed.profile.id,
            ProfilePhoto.deleted_at.is_(None),
        )
    )
    if photo is None:
        raise NotFound()
    return photo, managed.profile


@router.patch("/profiles/{profile_id}/photos/{photo_id}", response_model=PhotoOut)
async def update_photo(
    profile_id: uuid.UUID, photo_id: uuid.UUID, body: PhotoPatchIn, auth: Auth, db: DB, meta: Meta
) -> PhotoOut:
    photo, profile = await _managed_photo(db, auth, profile_id, photo_id)
    if body.is_primary:
        for other in await profiles.active_photos(db, profile.id):
            other.is_primary = other.id == photo.id
    if body.visibility is not None:
        photo.visibility = body.visibility.value
    if body.sort_order is not None:
        photo.sort_order = body.sort_order
    await audit.record(
        db,
        action="photo.update",
        resource_type="profile_photo",
        resource_id=str(photo.public_id),
        actor_user_id=auth.user.id,
        after=body.model_dump(mode="json", exclude_none=True),
        ip_hash=meta.ip_hash,
        request_id=meta.request_id,
    )
    return profiles.photo_out(photo)


@router.delete("/profiles/{profile_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(
    profile_id: uuid.UUID, photo_id: uuid.UUID, auth: Auth, db: DB, meta: Meta
) -> None:
    photo, profile = await _managed_photo(db, auth, profile_id, photo_id)
    photo.deleted_at = utcnow()
    was_primary, photo.is_primary = photo.is_primary, False
    await db.flush()
    remaining = await profiles.active_photos(db, profile.id)
    if was_primary and remaining:
        remaining[0].is_primary = True
    await storage.delete(photo.storage_key, photo.thumbnail_key)
    await audit.record(
        db,
        action="photo.delete",
        resource_type="profile_photo",
        resource_id=str(photo.public_id),
        actor_user_id=auth.user.id,
        ip_hash=meta.ip_hash,
        request_id=meta.request_id,
    )
    await profiles.refresh_completion(db, profile)


@router.get(
    "/media/photos/{photo_id}",
    responses={200: {"content": {"image/jpeg": {}}}},
    response_class=Response,
)
async def get_photo(
    photo_id: uuid.UUID,
    auth: Auth,
    db: DB,
    variant: Annotated[Literal["thumb", "full"], Query()] = "thumb",
) -> Response:
    """Stream a photo the caller is allowed to see; 404 otherwise (never reveal existence)."""
    photo = await db.scalar(
        select(ProfilePhoto).where(
            ProfilePhoto.public_id == photo_id, ProfilePhoto.deleted_at.is_(None)
        )
    )
    if photo is None:
        raise NotFound()
    profile = await db.get(Profile, photo.profile_id)
    if profile is None:
        raise NotFound()

    allowed = bool(auth.user.role_codes & {r.value for r in STAFF_ROLES})
    if not allowed:
        allowed = await role_for(db, auth.user, profile) is not None
    if not allowed:
        viewer = await db.scalar(select(Profile).where(Profile.owner_user_id == auth.user.id))
        allowed = (
            photo.moderation_status == ModerationStatus.APPROVED
            and photo.visibility == Visibility.MEMBERS
            and profiles.is_publicly_visible(profile)
            and viewer is not None
            and profiles.is_publicly_visible(viewer)
        )
    if not allowed:
        raise NotFound()

    data = await storage.get_bytes(photo.thumbnail_key if variant == "thumb" else photo.storage_key)
    if data is None:
        raise NotFound()
    return Response(
        content=data,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "private, max-age=300",
            "Content-Disposition": "inline",
            "X-Content-Type-Options": "nosniff",
        },
    )
