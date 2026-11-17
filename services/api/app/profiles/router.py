import uuid

from fastapi import APIRouter, status
from sqlalchemy import select

from app.audit import service as audit
from app.common.errors import AppError, Conflict, NotFound
from app.common.phone import normalize_phone
from app.delegation import service as delegation
from app.delegation.models import ALL_SCOPES, DelegatedAccess, DelegationKind, DelegationStatus
from app.entitlements.service import Entitlement, require_entitlement
from app.profiles import service
from app.profiles.access import load_managed, managed_profiles, role_for
from app.profiles.models import Profile
from app.profiles.options import CreatedFor, ProfileStatus, ProfileVisibility
from app.profiles.schemas import (
    BasicIn,
    CareerIn,
    CommunityIn,
    EducationIn,
    FamilyIn,
    LifestyleIn,
    MemberProfileOut,
    ProfileCreateIn,
    ProfileManageOut,
    ProfileSummaryOut,
    Section,
)
from app.security.deps import DB, Auth, Meta

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/managed", response_model=list[ProfileSummaryOut])
async def list_managed(auth: Auth, db: DB) -> list[ProfileSummaryOut]:
    """Profiles the caller owns, helps manage, or created and is waiting on consent for."""
    return [await service.summary_out(db, m) for m in await managed_profiles(db, auth.user)]


@router.post("", response_model=ProfileManageOut, status_code=status.HTTP_201_CREATED)
async def create_profile(body: ProfileCreateIn, auth: Auth, db: DB, meta: Meta) -> ProfileManageOut:
    user = auth.user
    await require_entitlement(db, user, Entitlement.PROFILE_CREATE)
    for_self = body.created_for == CreatedFor.SELF

    if for_self:
        if await db.scalar(select(Profile.id).where(Profile.owner_user_id == user.id)):
            raise Conflict("You already have a profile.", code="profile_exists")
        profile = Profile(
            owner_user_id=user.id,
            created_by_user_id=user.id,
            created_for=body.created_for.value,
            subject_name=body.subject_name,
            gender=body.gender.value if body.gender else None,
        )
    else:
        if not body.subject_phone:
            raise AppError(
                "Enter the mobile number of the person this profile is for.",
                code="subject_phone_required",
                status_code=422,
            )
        subject_phone = normalize_phone(body.subject_phone)
        if subject_phone == user.phone_e164:
            raise AppError(
                "Use “Myself” to create your own profile.", code="invalid_invitee", status_code=422
            )
        if await delegation.count_pending_creations(db, user) >= delegation.MAX_PENDING_CREATIONS:
            raise Conflict("Too many profiles are waiting for consent.", code="too_many_pending")
        profile = Profile(
            owner_user_id=None,
            created_by_user_id=user.id,
            subject_phone_e164=subject_phone,
            created_for=body.created_for.value,
            subject_name=body.subject_name,
            gender=body.gender.value if body.gender else None,
        )

    db.add(profile)
    await db.flush()
    await service.assign_launch_community(db, profile)

    if not for_self:
        assert profile.subject_phone_e164 is not None
        db.add(
            DelegatedAccess(
                profile_id=profile.id,
                kind=DelegationKind.SUBJECT_CONSENT,
                delegate_user_id=user.id,
                invited_phone_e164=profile.subject_phone_e164,
                invited_by_user_id=user.id,
                relationship=body.created_for.value,
                permission_scope=list(ALL_SCOPES),
                status=DelegationStatus.INVITED,
            )
        )
        await delegation.notify_invite(
            profile.subject_phone_e164, DelegationKind.SUBJECT_CONSENT, body.subject_name
        )

    await audit.record(
        db,
        action="profile.create",
        resource_type="profile",
        resource_id=str(profile.public_id),
        actor_user_id=user.id,
        after={"created_for": body.created_for.value, "subject_consent_pending": not for_self},
        ip_hash=meta.ip_hash,
        request_id=meta.request_id,
    )
    managed = await role_for(db, user, profile)
    assert managed is not None
    return await service.manage_out(db, managed)


@router.get("/{profile_id}", response_model=ProfileManageOut | MemberProfileOut)
async def get_profile(
    profile_id: uuid.UUID, auth: Auth, db: DB
) -> ProfileManageOut | MemberProfileOut:
    profile = await db.scalar(select(Profile).where(Profile.public_id == profile_id))
    if profile is None:
        raise NotFound()
    managed = await role_for(db, auth.user, profile)
    if managed is not None and profile.profile_status != ProfileStatus.ARCHIVED:
        return await service.manage_out(db, managed)
    # Other members: only approved, discoverable profiles, and only to members who are
    # themselves approved. Discovery rules (blocks, preferences) arrive in Phase 3.
    viewer = await db.scalar(select(Profile).where(Profile.owner_user_id == auth.user.id))
    if (
        not service.is_publicly_visible(profile)
        or viewer is None
        or not service.is_publicly_visible(viewer)
    ):
        raise NotFound()
    return await service.member_out(db, profile)


@router.get("/{profile_id}/preview", response_model=MemberProfileOut)
async def preview(profile_id: uuid.UUID, auth: Auth, db: DB) -> MemberProfileOut:
    """How other members will see this profile (photos only once approved)."""
    managed = await load_managed(db, auth.user, profile_id)
    return await service.member_out(db, managed.profile)


async def _put_section(
    profile_id: uuid.UUID, section: Section, body: object, auth: Auth, db: DB, meta: Meta
) -> ProfileManageOut:
    managed = await load_managed(db, auth.user, profile_id, for_update=True)
    await service.update_section(db, managed, section, body, actor=auth.user, meta=meta)  # type: ignore[arg-type]
    return await service.manage_out(db, managed)


@router.put("/{profile_id}/basic", response_model=ProfileManageOut)
async def put_basic(
    profile_id: uuid.UUID, body: BasicIn, auth: Auth, db: DB, meta: Meta
) -> ProfileManageOut:
    return await _put_section(profile_id, "basic", body, auth, db, meta)


@router.put("/{profile_id}/community", response_model=ProfileManageOut)
async def put_community(
    profile_id: uuid.UUID, body: CommunityIn, auth: Auth, db: DB, meta: Meta
) -> ProfileManageOut:
    return await _put_section(profile_id, "community", body, auth, db, meta)


@router.put("/{profile_id}/education", response_model=ProfileManageOut)
async def put_education(
    profile_id: uuid.UUID, body: EducationIn, auth: Auth, db: DB, meta: Meta
) -> ProfileManageOut:
    return await _put_section(profile_id, "education", body, auth, db, meta)


@router.put("/{profile_id}/career", response_model=ProfileManageOut)
async def put_career(
    profile_id: uuid.UUID, body: CareerIn, auth: Auth, db: DB, meta: Meta
) -> ProfileManageOut:
    return await _put_section(profile_id, "career", body, auth, db, meta)


@router.put("/{profile_id}/family", response_model=ProfileManageOut)
async def put_family(
    profile_id: uuid.UUID, body: FamilyIn, auth: Auth, db: DB, meta: Meta
) -> ProfileManageOut:
    return await _put_section(profile_id, "family", body, auth, db, meta)


@router.put("/{profile_id}/lifestyle", response_model=ProfileManageOut)
async def put_lifestyle(
    profile_id: uuid.UUID, body: LifestyleIn, auth: Auth, db: DB, meta: Meta
) -> ProfileManageOut:
    return await _put_section(profile_id, "lifestyle", body, auth, db, meta)


@router.post("/{profile_id}/submit", response_model=ProfileManageOut)
async def submit(profile_id: uuid.UUID, auth: Auth, db: DB, meta: Meta) -> ProfileManageOut:
    managed = await load_managed(db, auth.user, profile_id, for_update=True)
    await service.submit(db, managed, actor=auth.user, meta=meta)
    return await service.manage_out(db, managed)


async def _set_visibility(
    profile_id: uuid.UUID, visibility: ProfileVisibility, auth: Auth, db: DB, meta: Meta
) -> ProfileManageOut:
    managed = await load_managed(db, auth.user, profile_id, for_update=True)
    managed.require_owner()  # privacy controls belong to the adult, not helpers
    managed.require_editable()
    before = managed.profile.visibility
    managed.profile.visibility = visibility.value
    if before != visibility.value:
        await audit.record(
            db,
            action=f"profile.visibility.{visibility.value}",
            resource_type="profile",
            resource_id=str(managed.profile.public_id),
            actor_user_id=auth.user.id,
            before={"visibility": before},
            after={"visibility": visibility.value},
            ip_hash=meta.ip_hash,
            request_id=meta.request_id,
        )
    return await service.manage_out(db, managed)


@router.post("/{profile_id}/pause", response_model=ProfileManageOut)
async def pause(profile_id: uuid.UUID, auth: Auth, db: DB, meta: Meta) -> ProfileManageOut:
    """Hide the profile from discovery without deleting anything."""
    return await _set_visibility(profile_id, ProfileVisibility.PAUSED, auth, db, meta)


@router.post("/{profile_id}/resume", response_model=ProfileManageOut)
async def resume(profile_id: uuid.UUID, auth: Auth, db: DB, meta: Meta) -> ProfileManageOut:
    return await _set_visibility(profile_id, ProfileVisibility.DISCOVERABLE, auth, db, meta)
