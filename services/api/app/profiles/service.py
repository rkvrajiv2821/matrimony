from datetime import date
from enum import Enum
from typing import Any, get_args
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit
from app.common.errors import AppError, Conflict
from app.common.time import utcnow
from app.delegation.models import Scope
from app.media.models import ProfilePhoto
from app.profiles.access import Managed
from app.profiles.models import (
    Profile,
    ProfileCommunity,
    ProfileEducation,
    ProfileEmployment,
    ProfileFamilyDetails,
    ProfilePersonalDetails,
    ProfileStatusHistory,
    jsonable,
)
from app.profiles.options import (
    MIN_AGE,
    ModerationStatus,
    ProfileStatus,
    ProfileVisibility,
    Visibility,
)
from app.profiles.schemas import (
    BasicIn,
    CareerIn,
    CommunityIn,
    CompletionOut,
    EducationIn,
    FamilyIn,
    LifestyleIn,
    MemberProfileOut,
    PhotoOut,
    PlaceOut,
    ProfileManageOut,
    ProfileSummaryOut,
    Section,
)
from app.reference.models import CommunityTaxonomy, Location, LocationType, TaxonomyType
from app.security.deps import RequestMeta
from app.users.models import User

IST = ZoneInfo("Asia/Kolkata")
# Async sessions can't lazy-load: refresh these explicitly after creating or changing a profile.
PROFILE_RELATIONS = ("personal", "family", "education", "employment", "communities")


def _enum_of(annotation: Any) -> type[Enum] | None:
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return annotation
    for arg in get_args(annotation):
        found = _enum_of(arg)
        if found is not None:
            return found
    return None


def construct[M: BaseModel](cls: type[M], **values: Any) -> M:
    """Build a response model from trusted DB values.

    Text is not re-validated (rules may tighten after data was stored), but enum codes are
    converted so serialization is exact.
    """
    for name, field in cls.model_fields.items():
        enum = _enum_of(field.annotation)
        value = values.get(name)
        if enum is None or value is None:
            continue
        if isinstance(value, list):
            values[name] = [enum(v) for v in value]
        elif isinstance(value, str):
            values[name] = enum(value)
    return cls.model_construct(**values)


MAX_AGE = 80


class ProfileIncomplete(AppError):
    status_code = 422
    code = "profile_incomplete"
    message = "Please complete the required sections before submitting."


class InvalidField(AppError):
    status_code = 422
    code = "validation_error"


def today_ist() -> date:
    return utcnow().astimezone(IST).date()


def age_on(dob: date | None, today: date | None = None) -> int | None:
    if dob is None:
        return None
    t = today or today_ist()
    return t.year - dob.year - ((t.month, t.day) < (dob.month, dob.day))


# ------------------------------------------------------------------ status machine

# Allowed transitions -> who may trigger them.
TRANSITIONS: dict[tuple[str, str], str] = {
    (ProfileStatus.DRAFT, ProfileStatus.SUBMITTED): "member",
    (ProfileStatus.NEEDS_CHANGES, ProfileStatus.SUBMITTED): "member",
    (ProfileStatus.APPROVED, ProfileStatus.SUBMITTED): "system",  # material change -> re-review
    (ProfileStatus.SUBMITTED, ProfileStatus.APPROVED): "moderator",
    (ProfileStatus.SUBMITTED, ProfileStatus.NEEDS_CHANGES): "moderator",
    (ProfileStatus.DRAFT, ProfileStatus.ARCHIVED): "member",
    (ProfileStatus.APPROVED, ProfileStatus.SUSPENDED): "moderator",
    (ProfileStatus.SUSPENDED, ProfileStatus.APPROVED): "moderator",
}


async def transition(
    db: AsyncSession,
    profile: Profile,
    to: ProfileStatus,
    *,
    by: str,
    actor: User | None,
    meta: RequestMeta | None,
    reason_code: str | None = None,
    note: str | None = None,
) -> None:
    frm = profile.profile_status
    allowed_by = TRANSITIONS.get((frm, to.value))
    if allowed_by is None or allowed_by != by:
        raise Conflict(
            f"A profile that is {frm} can't become {to.value}.", code="invalid_transition"
        )
    now = utcnow()
    profile.profile_status = to.value
    profile.status_reason_code = reason_code
    profile.status_note = note
    if to == ProfileStatus.SUBMITTED:
        profile.submitted_at = now
    if to == ProfileStatus.APPROVED:
        profile.approved_at = now
    db.add(
        ProfileStatusHistory(
            profile_id=profile.id,
            from_status=frm,
            to_status=to.value,
            reason_code=reason_code,
            note=note,
            actor_user_id=actor.id if actor else None,
        )
    )
    await audit.record(
        db,
        action=f"profile.status.{to.value}",
        resource_type="profile",
        resource_id=str(profile.public_id),
        actor_user_id=actor.id if actor else None,
        before={"status": frm},
        after={"status": to.value, "reason_code": reason_code},
        ip_hash=meta.ip_hash if meta else None,
        request_id=meta.request_id if meta else None,
    )


# ------------------------------------------------------------------ reference lookups


async def location_by_code(
    db: AsyncSession, code: str | None, expected: LocationType, *, parent_id: int | None = None
) -> Location | None:
    if code is None:
        return None
    loc = await db.scalar(
        select(Location).where(
            Location.code == code, Location.type == expected.value, Location.active.is_(True)
        )
    )
    if loc is None or (parent_id is not None and loc.parent_id != parent_id):
        raise InvalidField(
            f"Unknown or mismatched {expected.value}.", details={"field": f"{expected.value}_code"}
        )
    return loc


async def launch_community(db: AsyncSession) -> CommunityTaxonomy:
    community = await db.scalar(
        select(CommunityTaxonomy)
        .where(
            CommunityTaxonomy.type == TaxonomyType.COMMUNITY,
            CommunityTaxonomy.active.is_(True),
        )
        .order_by(CommunityTaxonomy.sort_order, CommunityTaxonomy.id)
    )
    if community is None:
        raise Conflict("No launch community is configured.", code="community_not_configured")
    return community


async def assign_launch_community(db: AsyncSession, profile: Profile) -> None:
    community = await launch_community(db)
    db.add(ProfileCommunity(profile_id=profile.id, community_id=community.id, is_primary=True))
    await db.flush()
    await db.refresh(profile, list(PROFILE_RELATIONS))


# ------------------------------------------------------------------ sections

MATERIAL_FIELDS: dict[str, set[str]] = {
    "basic": {"subject_name", "display_name", "date_of_birth", "gender", "marital_status"},
    "community": {"sub_community_code"},
    "family": {"family_description"},
    "lifestyle": {"about_me"},
    "career": {"occupation", "employer"},
    "education": {"institution"},
}


async def _section_snapshot(db: AsyncSession, profile: Profile, section: Section) -> dict[str, Any]:
    view = await section_values(db, profile)
    model = view.get(section)
    return model.model_dump(mode="json") if model is not None else {}


async def section_values(db: AsyncSession, profile: Profile) -> dict[str, BaseModel | None]:
    """Current values of each editable section, in the same shape as the PUT bodies."""
    places = await _places(db, profile)
    sub = await _sub_community(db, profile)
    p = profile.personal
    e = profile.education
    c = profile.employment
    f = profile.family
    basic: BaseModel | None = None
    if profile.date_of_birth and profile.gender and profile.display_name:
        basic = construct(
            BasicIn,
            subject_name=profile.subject_name,
            display_name=profile.display_name,
            date_of_birth=profile.date_of_birth,
            gender=profile.gender,
            marital_status=profile.marital_status,
            has_children=profile.has_children,
            height_cm=profile.height_cm,
            mother_tongue=profile.mother_tongue,
            current_country=profile.current_country,
            state_code=_code(places.get(profile.state_id or 0)),
            district_code=_code(places.get(profile.district_id or 0)),
            city_code=_code(places.get(profile.city_id or 0)),
        )
    primary = next((pc for pc in profile.communities if pc.is_primary), None)
    return {
        "basic": basic,
        "community": CommunityIn(
            sub_community_code=sub.code if sub else None,
            visibility=Visibility(primary.visibility) if primary else Visibility.MEMBERS,
        ),
        "education": construct(
            EducationIn,
            qualification=e.qualification,
            field_of_study=e.field_of_study,
            institution=e.institution,
            year_completed=e.year_completed,
            visibility=e.visibility,
        )
        if e
        else None,
        "career": construct(
            CareerIn,
            employment_type=c.employment_type,
            occupation=c.occupation,
            industry=c.industry,
            employer=c.employer,
            work_city_code=_code(places.get(c.work_city_id or 0)),
            income_band=c.income_band,
            visibility=c.visibility,
        )
        if c
        else None,
        "family": construct(
            FamilyIn,
            family_type=f.family_type,
            family_values=f.family_values,
            native_district_code=_code(places.get(f.native_district_id or 0)),
            father_occupation=f.father_occupation,
            mother_occupation=f.mother_occupation,
            siblings_count=f.siblings_count,
            siblings_married=f.siblings_married,
            family_description=f.family_description,
            visibility=f.visibility,
        )
        if f
        else None,
        "lifestyle": construct(
            LifestyleIn,
            physical_status=p.physical_status,
            languages=p.languages or [],
            diet=p.diet,
            smoking=p.smoking,
            drinking=p.drinking,
            interests=p.interests or [],
            about_me=p.about_me,
        )
        if p
        else None,
    }


def _code(loc: Location | None) -> str | None:
    return loc.code if loc else None


async def update_section(
    db: AsyncSession,
    managed: Managed,
    section: Section,
    body: BaseModel,
    *,
    actor: User,
    meta: RequestMeta,
) -> None:
    managed.require(Scope.EDIT_PROFILE)
    managed.require_editable()
    profile = managed.profile
    before = await _section_snapshot(db, profile, section)

    if isinstance(body, BasicIn):
        await _apply_basic(db, profile, body)
    elif isinstance(body, CommunityIn):
        await _apply_community(db, profile, body)
    elif isinstance(body, EducationIn):
        _upsert(profile, "education", ProfileEducation, body.model_dump())
    elif isinstance(body, CareerIn):
        work_city = await location_by_code(db, body.work_city_code, LocationType.CITY)
        data = body.model_dump(exclude={"work_city_code"})
        data["work_city_id"] = work_city.id if work_city else None
        _upsert(profile, "employment", ProfileEmployment, data)
    elif isinstance(body, FamilyIn):
        native = await location_by_code(db, body.native_district_code, LocationType.DISTRICT)
        data = body.model_dump(exclude={"native_district_code"})
        data["native_district_id"] = native.id if native else None
        _upsert(profile, "family", ProfileFamilyDetails, data)
    elif isinstance(body, LifestyleIn):
        _upsert(profile, "personal", ProfilePersonalDetails, body.model_dump(mode="json"))

    await db.flush()
    await db.refresh(profile, list(PROFILE_RELATIONS))
    after = await _section_snapshot(db, profile, section)
    changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
    if not changed:
        return

    await audit.record(
        db,
        action=f"profile.section.{section}",
        resource_type="profile",
        resource_id=str(profile.public_id),
        actor_user_id=actor.id,
        before={k: jsonable(before.get(k)) for k in changed},
        after={k: jsonable(after.get(k)) for k in changed},
        ip_hash=meta.ip_hash,
        request_id=meta.request_id,
    )
    if profile.profile_status == ProfileStatus.APPROVED and changed & MATERIAL_FIELDS.get(
        section, set()
    ):
        await transition(
            db,
            profile,
            ProfileStatus.SUBMITTED,
            by="system",
            actor=actor,
            meta=meta,
            reason_code="material_change",
        )
    await refresh_completion(db, profile)


def _upsert(profile: Profile, attr: str, model: type[Any], data: dict[str, Any]) -> None:
    row = getattr(profile, attr)
    if row is None:
        setattr(profile, attr, model(**data))
    else:
        for k, v in data.items():
            setattr(row, k, v)


async def _apply_basic(db: AsyncSession, profile: Profile, body: BasicIn) -> None:
    age = age_on(body.date_of_birth)
    assert age is not None
    if age < MIN_AGE:
        raise InvalidField(
            "Profiles are only for adults aged 18 or over.",
            code="underage",
            details={"field": "date_of_birth"},
        )
    if age > MAX_AGE:
        raise InvalidField("Please check the date of birth.", details={"field": "date_of_birth"})

    country = await location_by_code(db, body.current_country, LocationType.COUNTRY)
    if country is None:
        raise InvalidField("Unknown country.", details={"field": "current_country"})
    state = district = city = None
    if body.state_code:
        state = await location_by_code(
            db, body.state_code, LocationType.STATE, parent_id=country.id
        )
    if body.district_code:
        if state is None:
            raise InvalidField("Choose a state first.", details={"field": "district_code"})
        district = await location_by_code(
            db, body.district_code, LocationType.DISTRICT, parent_id=state.id
        )
    if body.city_code:
        if district is None:
            raise InvalidField("Choose a district first.", details={"field": "city_code"})
        city = await location_by_code(db, body.city_code, LocationType.CITY, parent_id=district.id)

    profile.subject_name = body.subject_name
    profile.display_name = body.display_name
    profile.date_of_birth = body.date_of_birth
    profile.gender = body.gender.value
    profile.marital_status = body.marital_status.value
    profile.has_children = body.has_children
    profile.height_cm = body.height_cm
    profile.mother_tongue = body.mother_tongue.value
    profile.current_country = body.current_country
    profile.state_id = state.id if state else None
    profile.district_id = district.id if district else None
    profile.city_id = city.id if city else None


async def _apply_community(db: AsyncSession, profile: Profile, body: CommunityIn) -> None:
    primary = next((pc for pc in profile.communities if pc.is_primary), None)
    if primary is None:
        await assign_launch_community(db, profile)
        primary = next(pc for pc in profile.communities if pc.is_primary)
    primary.visibility = body.visibility.value
    for pc in [pc for pc in profile.communities if not pc.is_primary]:
        profile.communities.remove(pc)
    if body.sub_community_code:
        sub = await db.scalar(
            select(CommunityTaxonomy).where(
                CommunityTaxonomy.code == body.sub_community_code,
                CommunityTaxonomy.type == TaxonomyType.SUB_COMMUNITY,
                CommunityTaxonomy.parent_id == primary.community_id,
                CommunityTaxonomy.active.is_(True),
            )
        )
        if sub is None:
            raise InvalidField("Unknown sub-community.", details={"field": "sub_community_code"})
        await db.flush()
        profile.communities.append(
            ProfileCommunity(
                profile_id=profile.id,
                community_id=sub.id,
                is_primary=False,
                visibility=body.visibility.value,
            )
        )


# ------------------------------------------------------------------ completion

REQUIRED_ITEMS = ["basic", "location", "community", "education", "career", "photo"]
OPTIONAL_ITEMS = ["family", "lifestyle", "about_me", "occupation", "preferences"]


async def active_photos(db: AsyncSession, profile_id: int) -> list[ProfilePhoto]:
    return list(
        await db.scalars(
            select(ProfilePhoto)
            .where(ProfilePhoto.profile_id == profile_id, ProfilePhoto.deleted_at.is_(None))
            .order_by(ProfilePhoto.is_primary.desc(), ProfilePhoto.sort_order, ProfilePhoto.id)
        )
    )


async def completion(db: AsyncSession, profile: Profile) -> CompletionOut:
    from app.preferences.models import PartnerPreference  # local: avoid import cycle

    photos = [p for p in await active_photos(db, profile.id) if p.moderation_status != "rejected"]
    has_prefs = await db.scalar(
        select(PartnerPreference.id).where(
            PartnerPreference.profile_id == profile.id, PartnerPreference.active.is_(True)
        )
    )
    basic = all(
        v is not None
        for v in (
            profile.display_name,
            profile.date_of_birth,
            profile.gender,
            profile.marital_status,
            profile.height_cm,
            profile.mother_tongue,
        )
    )
    in_india = profile.current_country == "IN"
    location = profile.current_country is not None and (
        not in_india or profile.state_id is not None
    )
    sections = {
        "basic": basic,
        "location": location,
        "community": any(pc.is_primary for pc in profile.communities),
        "education": profile.education is not None,
        "career": profile.employment is not None,
        "photo": bool(photos),
        "family": profile.family is not None and profile.family.family_type is not None,
        "lifestyle": profile.personal is not None and profile.personal.diet is not None,
        "about_me": bool(profile.personal and profile.personal.about_me),
        "occupation": bool(profile.employment and profile.employment.occupation),
        "preferences": has_prefs is not None,
    }
    req_done = sum(sections[k] for k in REQUIRED_ITEMS)
    opt_done = sum(sections[k] for k in OPTIONAL_ITEMS)
    percent = round(70 * req_done / len(REQUIRED_ITEMS) + 30 * opt_done / len(OPTIONAL_ITEMS))
    return CompletionOut(
        percent=percent,
        missing_required=[k for k in REQUIRED_ITEMS if not sections[k]],
        sections=sections,
    )


async def refresh_completion(db: AsyncSession, profile: Profile) -> CompletionOut:
    result = await completion(db, profile)
    profile.completion_percent = result.percent
    return result


async def submit(db: AsyncSession, managed: Managed, *, actor: User, meta: RequestMeta) -> None:
    managed.require(Scope.EDIT_PROFILE)
    managed.require_editable()
    profile = managed.profile
    result = await refresh_completion(db, profile)
    if result.missing_required:
        raise ProfileIncomplete(details={"missing": result.missing_required})
    age = age_on(profile.date_of_birth)
    if age is None or age < MIN_AGE:  # re-checked at publication time (PRD §13)
        raise InvalidField("Profiles are only for adults aged 18 or over.", code="underage")
    await transition(db, profile, ProfileStatus.SUBMITTED, by="member", actor=actor, meta=meta)


# ------------------------------------------------------------------ serialization


def photo_out(photo: ProfilePhoto) -> PhotoOut:
    base = f"/api/v1/media/photos/{photo.public_id}"
    return PhotoOut(
        id=photo.public_id,
        thumb_url=f"{base}?variant=thumb",
        full_url=f"{base}?variant=full",
        is_primary=photo.is_primary,
        visibility=Visibility(photo.visibility),
        moderation_status=ModerationStatus(photo.moderation_status),
        moderation_reason=photo.moderation_reason,
        width=photo.width,
        height=photo.height,
    )


async def _places(db: AsyncSession, profile: Profile) -> dict[int, Location]:
    ids = {
        profile.state_id,
        profile.district_id,
        profile.city_id,
        profile.employment.work_city_id if profile.employment else None,
        profile.family.native_district_id if profile.family else None,
    } - {None}
    if not ids:
        return {}
    rows = await db.scalars(select(Location).where(Location.id.in_(ids)))
    return {loc.id: loc for loc in rows}


def _place(loc: Location | None) -> PlaceOut | None:
    return PlaceOut(code=loc.code, name_en=loc.name_en, name_ta=loc.name_ta) if loc else None


async def _taxonomy(db: AsyncSession, profile: Profile, primary: bool) -> CommunityTaxonomy | None:
    pc = next((c for c in profile.communities if c.is_primary == primary), None)
    return await db.get(CommunityTaxonomy, pc.community_id) if pc else None


async def _sub_community(db: AsyncSession, profile: Profile) -> CommunityTaxonomy | None:
    return await _taxonomy(db, profile, primary=False)


def _label(t: CommunityTaxonomy | None) -> PlaceOut | None:
    return PlaceOut(code=t.code, name_en=t.label_en, name_ta=t.label_ta) if t else None


async def manage_out(db: AsyncSession, managed: Managed) -> ProfileManageOut:
    profile = managed.profile
    places = await _places(db, profile)
    values = await section_values(db, profile)
    comp = await refresh_completion(db, profile)
    return ProfileManageOut(
        id=profile.public_id,
        my_role=managed.role.value,
        my_scopes=sorted(managed.scopes),
        created_for=profile.created_for,
        subject_name=profile.subject_name,
        display_name=profile.display_name,
        date_of_birth=profile.date_of_birth,
        age=age_on(profile.date_of_birth),
        gender=profile.gender,
        marital_status=profile.marital_status,
        has_children=profile.has_children,
        height_cm=profile.height_cm,
        mother_tongue=profile.mother_tongue,
        current_country=profile.current_country,
        state=_place(places.get(profile.state_id or 0)),
        district=_place(places.get(profile.district_id or 0)),
        city=_place(places.get(profile.city_id or 0)),
        community=values["community"],
        community_label=_label(await _taxonomy(db, profile, primary=True)),
        education=values["education"],
        career=values["career"],
        work_city=_place(
            places.get(profile.employment.work_city_id or 0) if profile.employment else None
        ),
        family=values["family"],
        native_district=_place(
            places.get(profile.family.native_district_id or 0) if profile.family else None
        ),
        lifestyle=values["lifestyle"],
        photos=[photo_out(p) for p in await active_photos(db, profile.id)],
        status=profile.profile_status,
        status_reason_code=profile.status_reason_code,
        status_note=profile.status_note,
        visibility=profile.visibility,
        completion=comp,
        subject_consent_pending=profile.owner_user_id is None,
        submitted_at=profile.submitted_at,
        approved_at=profile.approved_at,
    )


async def summary_out(db: AsyncSession, managed: Managed) -> ProfileSummaryOut:
    profile = managed.profile
    photos = await active_photos(db, profile.id)
    return ProfileSummaryOut(
        id=profile.public_id,
        my_role=managed.role.value,
        created_for=profile.created_for,
        subject_name=profile.subject_name,
        display_name=profile.display_name,
        status=profile.profile_status,
        visibility=profile.visibility,
        completion_percent=profile.completion_percent,
        primary_photo_url=photo_out(photos[0]).thumb_url if photos else None,
        subject_consent_pending=profile.owner_user_id is None,
    )


def _visible(visibility: str | None, *, connected: bool) -> bool:
    return visibility == Visibility.MEMBERS or (connected and visibility == Visibility.CONNECTIONS)


async def member_out(
    db: AsyncSession, profile: Profile, *, connected: bool = False
) -> MemberProfileOut:
    """The profile as another member sees it. `connected` arrives with interests (Phase 4)."""
    places = await _places(db, profile)
    primary = next((pc for pc in profile.communities if pc.is_primary), None)
    show_community = primary is not None and _visible(primary.visibility, connected=connected)
    e, c, f, p = profile.education, profile.employment, profile.family, profile.personal
    edu_private = e is None or not _visible(e.visibility, connected=connected)
    career_private = c is None or not _visible(c.visibility, connected=connected)
    family_visible = f is not None and _visible(f.visibility, connected=connected)
    photos = [
        photo_out(ph)
        for ph in await active_photos(db, profile.id)
        if ph.moderation_status == ModerationStatus.APPROVED
        and _visible(ph.visibility, connected=connected)
    ]
    lifestyle = None
    if p is not None:
        lifestyle = construct(
            LifestyleIn,
            physical_status=p.physical_status,
            languages=p.languages or [],
            diet=p.diet,
            smoking=p.smoking,
            drinking=p.drinking,
            interests=p.interests or [],
            about_me=p.about_me,
        )
    family = None
    if family_visible and f is not None:
        family = construct(
            FamilyIn,
            family_type=f.family_type,
            family_values=f.family_values,
            native_district_code=None,
            father_occupation=f.father_occupation,
            mother_occupation=f.mother_occupation,
            siblings_count=f.siblings_count,
            siblings_married=f.siblings_married,
            family_description=f.family_description,
            visibility=f.visibility,
        )
    return MemberProfileOut(
        id=profile.public_id,
        display_name=profile.display_name or "",
        age=age_on(profile.date_of_birth),
        gender=profile.gender,
        marital_status=profile.marital_status,
        has_children=profile.has_children,
        height_cm=profile.height_cm,
        mother_tongue=profile.mother_tongue,
        current_country=profile.current_country,
        state=_place(places.get(profile.state_id or 0)),
        district=_place(places.get(profile.district_id or 0)),
        city=_place(places.get(profile.city_id or 0)),
        community_label=_label(await _taxonomy(db, profile, True)) if show_community else None,
        sub_community_label=_label(await _taxonomy(db, profile, False)) if show_community else None,
        qualification=e.qualification if e else None,
        field_of_study=e.field_of_study if e else None,
        institution=None if edu_private or e is None else e.institution,
        employment_type=c.employment_type if c else None,
        occupation=c.occupation if c else None,
        industry=c.industry if c else None,
        employer=None if career_private or c is None else c.employer,
        income_band=None if career_private or c is None else c.income_band,
        family=family,
        native_district=_place(places.get(f.native_district_id or 0))
        if family_visible and f
        else None,
        lifestyle=lifestyle,
        photos=photos,
        created_for=profile.created_for,
    )


def is_publicly_visible(profile: Profile) -> bool:
    return (
        profile.profile_status == ProfileStatus.APPROVED
        and profile.visibility == ProfileVisibility.DISCOVERABLE
        and profile.owner_user_id is not None
    )
