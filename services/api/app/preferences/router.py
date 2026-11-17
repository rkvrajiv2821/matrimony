"""Partner preferences (PRD §4.3): must-have / preferred / flexible criteria."""

import uuid
from typing import Annotated, Literal, Self

from fastapi import APIRouter, status
from pydantic import BaseModel, Field, StringConstraints, model_validator
from sqlalchemy import func, select

from app.audit import service as audit
from app.common.errors import AppError, Conflict, NotFound
from app.delegation.models import Scope
from app.preferences.models import PartnerPreference, PreferenceCommunityValue
from app.profiles import service as profiles
from app.profiles.access import load_managed
from app.profiles.models import Profile
from app.profiles.options import (
    MAX_HEIGHT_CM,
    MIN_AGE,
    MIN_HEIGHT_CM,
    Diet,
    EducationLevel,
    EmploymentType,
    IncomeBand,
    Language,
    MaritalStatus,
)
from app.reference.models import CommunityTaxonomy, Location, LocationType, TaxonomyType
from app.security.deps import DB, Auth, Meta

router = APIRouter(tags=["preferences"])

Criterion = Literal[
    "age",
    "height",
    "marital_status",
    "location",
    "education",
    "employment",
    "income",
    "diet",
    "mother_tongue",
    "community",
]
Code = Annotated[str, StringConstraints(max_length=50, pattern=r"^[a-z0-9_-]+$")]
MAX_PREFERENCES = 5


class PreferenceIn(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)] = (
        "Default"
    )
    is_default: bool = True
    age_min: int | None = Field(default=None, ge=MIN_AGE, le=80)
    age_max: int | None = Field(default=None, ge=MIN_AGE, le=80)
    height_min_cm: int | None = Field(default=None, ge=MIN_HEIGHT_CM, le=MAX_HEIGHT_CM)
    height_max_cm: int | None = Field(default=None, ge=MIN_HEIGHT_CM, le=MAX_HEIGHT_CM)
    marital_statuses: list[MaritalStatus] = Field(default_factory=list, max_length=10)
    district_codes: list[Code] = Field(default_factory=list, max_length=40)
    countries: list[Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]] = Field(
        default_factory=list, max_length=20
    )
    education_levels: list[EducationLevel] = Field(default_factory=list, max_length=10)
    employment_types: list[EmploymentType] = Field(default_factory=list, max_length=10)
    income_bands: list[IncomeBand] = Field(default_factory=list, max_length=10)
    diets: list[Diet] = Field(default_factory=list, max_length=10)
    mother_tongues: list[Language] = Field(default_factory=list, max_length=10)
    sub_community_codes: list[Code] = Field(default_factory=list, max_length=20)
    must_have: list[Criterion] = Field(default_factory=list)
    preferred: list[Criterion] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.age_min and self.age_max and self.age_min > self.age_max:
            raise ValueError("age_min must not exceed age_max")
        if self.height_min_cm and self.height_max_cm and self.height_min_cm > self.height_max_cm:
            raise ValueError("height_min_cm must not exceed height_max_cm")
        overlap = set(self.must_have) & set(self.preferred)
        if overlap:
            raise ValueError(f"criteria cannot be both must-have and preferred: {sorted(overlap)}")
        return self


class PreferenceOut(PreferenceIn):
    id: uuid.UUID
    flexible: list[Criterion]


ALL_CRITERIA: list[str] = list(Criterion.__args__)  # type: ignore[attr-defined]


def _out(pref: PartnerPreference, sub_codes: list[str]) -> PreferenceOut:
    rules = pref.location_rules or {}
    must = pref.must_have or []
    preferred = pref.preferred or []
    return PreferenceOut(
        id=pref.public_id,
        name=pref.name,
        is_default=pref.is_default,
        age_min=pref.age_min,
        age_max=pref.age_max,
        height_min_cm=pref.height_min_cm,
        height_max_cm=pref.height_max_cm,
        marital_statuses=pref.marital_statuses or [],
        district_codes=rules.get("district_codes", []),
        countries=rules.get("countries", []),
        education_levels=pref.education_levels or [],
        employment_types=pref.employment_types or [],
        income_bands=pref.income_bands or [],
        diets=pref.diets or [],
        mother_tongues=pref.mother_tongues or [],
        sub_community_codes=sub_codes,
        must_have=must,
        preferred=preferred,
        flexible=[c for c in ALL_CRITERIA if c not in must and c not in preferred],
    )


async def _sub_codes(db: DB, pref: PartnerPreference) -> list[str]:
    ids = [v.community_id for v in pref.community_values]
    if not ids:
        return []
    return list(
        await db.scalars(select(CommunityTaxonomy.code).where(CommunityTaxonomy.id.in_(ids)))
    )


async def _apply(db: DB, pref: PartnerPreference, body: PreferenceIn) -> None:
    if body.district_codes:
        found = set(
            await db.scalars(
                select(Location.code).where(
                    Location.code.in_(body.district_codes),
                    Location.type == LocationType.DISTRICT,
                )
            )
        )
        unknown = sorted(set(body.district_codes) - found)
        if unknown:
            raise AppError(
                "Unknown district.",
                code="validation_error",
                status_code=422,
                details={"field": "district_codes", "unknown": unknown},
            )
    sub_ids: list[int] = []
    if body.sub_community_codes:
        rows = (
            await db.execute(
                select(CommunityTaxonomy.id, CommunityTaxonomy.code).where(
                    CommunityTaxonomy.code.in_(body.sub_community_codes),
                    CommunityTaxonomy.type == TaxonomyType.SUB_COMMUNITY,
                )
            )
        ).all()
        if len(rows) != len(set(body.sub_community_codes)):
            raise AppError(
                "Unknown sub-community.",
                code="validation_error",
                status_code=422,
                details={"field": "sub_community_codes"},
            )
        sub_ids = [r[0] for r in rows]

    pref.name = body.name
    pref.age_min, pref.age_max = body.age_min, body.age_max
    pref.height_min_cm, pref.height_max_cm = body.height_min_cm, body.height_max_cm
    pref.marital_statuses = [m.value for m in body.marital_statuses]
    pref.location_rules = {"district_codes": body.district_codes, "countries": body.countries}
    pref.education_levels = [e.value for e in body.education_levels]
    pref.employment_types = [e.value for e in body.employment_types]
    pref.income_bands = [i.value for i in body.income_bands]
    pref.diets = [d.value for d in body.diets]
    pref.mother_tongues = [m.value for m in body.mother_tongues]
    pref.must_have = list(body.must_have)
    pref.preferred = list(body.preferred)
    pref.community_values.clear()
    await db.flush()
    for cid in sub_ids:
        pref.community_values.append(
            PreferenceCommunityValue(preference_id=pref.id, community_id=cid)
        )


async def _make_default(db: DB, pref: PartnerPreference) -> None:
    others = await db.scalars(
        select(PartnerPreference).where(
            PartnerPreference.profile_id == pref.profile_id,
            PartnerPreference.id != pref.id,
            PartnerPreference.is_default.is_(True),
        )
    )
    for o in others:
        o.is_default = False
    pref.is_default = True


async def _audit(
    db: DB, action: str, profile: Profile, pref: PartnerPreference, auth: Auth, meta: Meta
) -> None:
    await audit.record(
        db,
        action=action,
        resource_type="partner_preference",
        resource_id=str(pref.public_id),
        actor_user_id=auth.user.id,
        after={"profile": str(profile.public_id)},
        ip_hash=meta.ip_hash,
        request_id=meta.request_id,
    )


@router.get("/profiles/{profile_id}/preferences", response_model=list[PreferenceOut])
async def list_preferences(profile_id: uuid.UUID, auth: Auth, db: DB) -> list[PreferenceOut]:
    managed = await load_managed(db, auth.user, profile_id)
    rows = await db.scalars(
        select(PartnerPreference)
        .where(PartnerPreference.profile_id == managed.profile.id, PartnerPreference.active)
        .order_by(PartnerPreference.is_default.desc(), PartnerPreference.id)
    )
    return [_out(p, await _sub_codes(db, p)) for p in rows]


@router.post(
    "/profiles/{profile_id}/preferences",
    response_model=PreferenceOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_preference(
    profile_id: uuid.UUID, body: PreferenceIn, auth: Auth, db: DB, meta: Meta
) -> PreferenceOut:
    managed = await load_managed(db, auth.user, profile_id, for_update=True)
    managed.require(Scope.MANAGE_PREFERENCES)
    profile = managed.profile
    count = await db.scalar(
        select(func.count())
        .select_from(PartnerPreference)
        .where(PartnerPreference.profile_id == profile.id, PartnerPreference.active)
    )
    if (count or 0) >= MAX_PREFERENCES:
        raise Conflict("You can save up to 5 preference sets.", code="too_many_preferences")
    pref = PartnerPreference(profile_id=profile.id, is_default=False)
    db.add(pref)
    await db.flush()
    await db.refresh(pref, ["community_values"])
    await _apply(db, pref, body)
    if body.is_default or not count:
        await _make_default(db, pref)
    await _audit(db, "preference.create", profile, pref, auth, meta)
    await profiles.refresh_completion(db, profile)
    return _out(pref, await _sub_codes(db, pref))


async def _load_pref(db: DB, auth: Auth, pref_id: uuid.UUID) -> tuple[PartnerPreference, Profile]:
    pref = await db.scalar(
        select(PartnerPreference).where(
            PartnerPreference.public_id == pref_id, PartnerPreference.active
        )
    )
    if pref is None:
        raise NotFound()
    profile = await db.get(Profile, pref.profile_id)
    if profile is None:
        raise NotFound()
    managed = await load_managed(db, auth.user, profile.public_id)  # 404 if not a manager
    managed.require(Scope.MANAGE_PREFERENCES)
    return pref, profile


@router.put("/preferences/{preference_id}", response_model=PreferenceOut)
async def update_preference(
    preference_id: uuid.UUID, body: PreferenceIn, auth: Auth, db: DB, meta: Meta
) -> PreferenceOut:
    pref, profile = await _load_pref(db, auth, preference_id)
    await _apply(db, pref, body)
    if body.is_default:
        await _make_default(db, pref)
    await _audit(db, "preference.update", profile, pref, auth, meta)
    return _out(pref, await _sub_codes(db, pref))


@router.delete("/preferences/{preference_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_preference(preference_id: uuid.UUID, auth: Auth, db: DB, meta: Meta) -> None:
    pref, profile = await _load_pref(db, auth, preference_id)
    pref.active = False
    if pref.is_default:
        pref.is_default = False
        nxt = await db.scalar(
            select(PartnerPreference).where(
                PartnerPreference.profile_id == profile.id,
                PartnerPreference.active,
                PartnerPreference.id != pref.id,
            )
        )
        if nxt is not None:
            nxt.is_default = True
    await _audit(db, "preference.delete", profile, pref, auth, meta)
    await profiles.refresh_completion(db, profile)
