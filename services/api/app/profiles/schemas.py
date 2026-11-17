import re
import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, StringConstraints, field_validator
from pydantic_core import PydanticCustomError

from app.delegation.models import Scope
from app.profiles.options import (
    CreatedFor,
    Diet,
    EducationLevel,
    EmploymentType,
    FamilyType,
    FamilyValues,
    FieldOfStudy,
    Gender,
    Habit,
    IncomeBand,
    Industry,
    Interest,
    MaritalStatus,
    ModerationStatus,
    PhysicalStatus,
    ProfileStatus,
    ProfileVisibility,
    ReviewReason,
    SpokenLanguage,
    Visibility,
)

# Contact details must be shared deliberately in chat, never embedded in profile text (PRD §4.7).
_PHONE_LIKE = re.compile(r"(?:\+?\d[\s\-().]?){10,}")
_EMAIL_LIKE = re.compile(r"[\w.+-]+\s*(?:@|\(at\)|\[at\])\s*[\w-]+\s*(?:\.|\(dot\))\s*\w+", re.I)
_URL_LIKE = re.compile(r"https?://|www\.|wa\.me|t\.me/|instagram\.com|facebook\.com", re.I)


CONTACT_ERROR = "contact_details_not_allowed"


def _no_contact_details(value: str | None) -> str | None:
    if value and (
        _PHONE_LIKE.search(value) or _EMAIL_LIKE.search(value) or _URL_LIKE.search(value)
    ):
        raise PydanticCustomError(
            CONTACT_ERROR,
            "Please remove phone numbers, email addresses and links from profile text.",
        )
    return value


Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
ShortText = Annotated[
    str | None,
    StringConstraints(strip_whitespace=True, max_length=100),
    AfterValidator(_no_contact_details),
]
LongText = Annotated[
    str | None,
    StringConstraints(strip_whitespace=True, max_length=1000),
    AfterValidator(_no_contact_details),
]
Code = Annotated[str, StringConstraints(max_length=50, pattern=r"^[a-z0-9_-]+$")]


# ---------------------------------------------------------------- create


class ProfileCreateIn(BaseModel):
    created_for: CreatedFor
    subject_name: Name
    # Required when creating for someone else: the adult must consent from their own phone.
    subject_phone: str | None = Field(default=None, max_length=20)
    gender: Gender | None = None


# ---------------------------------------------------------------- sections (PUT = replace)


class BasicIn(BaseModel):
    subject_name: Name
    display_name: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=2, max_length=60),
        AfterValidator(_no_contact_details),
    ]
    date_of_birth: date
    gender: Gender
    marital_status: MaritalStatus
    has_children: bool | None = None
    height_cm: int = Field(ge=120, le=220)
    mother_tongue: SpokenLanguage
    current_country: str = Field(pattern=r"^[A-Z]{2}$")
    state_code: Code | None = None
    district_code: Code | None = None
    city_code: Code | None = None


class CommunityIn(BaseModel):
    sub_community_code: Code | None = None
    visibility: Visibility = Visibility.MEMBERS


class EducationIn(BaseModel):
    qualification: EducationLevel
    field_of_study: FieldOfStudy | None = None
    institution: ShortText = None
    year_completed: int | None = Field(default=None, ge=1960, le=2100)
    visibility: Visibility = Visibility.MEMBERS


class CareerIn(BaseModel):
    employment_type: EmploymentType
    occupation: ShortText = None
    industry: Industry | None = None
    employer: ShortText = None
    work_city_code: Code | None = None
    income_band: IncomeBand | None = None
    # Applies to employer and income band.
    visibility: Visibility = Visibility.MEMBERS


class FamilyIn(BaseModel):
    family_type: FamilyType | None = None
    family_values: FamilyValues | None = None
    native_district_code: Code | None = None
    father_occupation: ShortText = None
    mother_occupation: ShortText = None
    siblings_count: int | None = Field(default=None, ge=0, le=20)
    siblings_married: int | None = Field(default=None, ge=0, le=20)
    family_description: LongText = None
    visibility: Visibility = Visibility.MEMBERS


class LifestyleIn(BaseModel):
    physical_status: PhysicalStatus | None = None
    languages: list[SpokenLanguage] = Field(default_factory=list, max_length=8)
    diet: Diet | None = None
    smoking: Habit | None = None
    drinking: Habit | None = None
    interests: list[Interest] = Field(default_factory=list, max_length=12)
    about_me: LongText = None

    @field_validator("languages", "interests")
    @classmethod
    def _dedupe(cls, v: list[str]) -> list[str]:
        return list(dict.fromkeys(v))


Section = Literal["basic", "community", "education", "career", "family", "lifestyle"]


# ---------------------------------------------------------------- outputs


class PlaceOut(BaseModel):
    code: str
    name_en: str
    name_ta: str


class PhotoOut(BaseModel):
    id: uuid.UUID
    thumb_url: str
    full_url: str
    is_primary: bool
    visibility: Visibility
    moderation_status: ModerationStatus
    moderation_reason: ReviewReason | None = None
    width: int
    height: int


class CompletionOut(BaseModel):
    percent: int
    missing_required: list[str]
    sections: dict[str, bool]


class DelegateSummary(BaseModel):
    id: uuid.UUID
    relationship: str
    status: str
    scopes: list[Scope]
    phone_masked: str | None
    is_me: bool


class ProfileManageOut(BaseModel):
    """Everything the owner (or a permitted helper) can see and edit."""

    id: uuid.UUID
    my_role: Literal["owner", "delegate", "creator_pending", "staff"]
    my_scopes: list[Scope]
    created_for: CreatedFor
    subject_name: str
    display_name: str | None
    date_of_birth: date | None
    age: int | None
    gender: Gender | None
    marital_status: MaritalStatus | None
    has_children: bool | None
    height_cm: int | None
    mother_tongue: SpokenLanguage | None
    current_country: str | None
    state: PlaceOut | None
    district: PlaceOut | None
    city: PlaceOut | None
    community: CommunityIn | None
    community_label: PlaceOut | None
    education: EducationIn | None
    career: CareerIn | None
    work_city: PlaceOut | None
    family: FamilyIn | None
    native_district: PlaceOut | None
    lifestyle: LifestyleIn | None
    photos: list[PhotoOut]
    status: ProfileStatus
    status_reason_code: ReviewReason | str | None
    status_note: str | None
    visibility: ProfileVisibility
    completion: CompletionOut
    subject_consent_pending: bool
    submitted_at: datetime | None
    approved_at: datetime | None


class ProfileSummaryOut(BaseModel):
    id: uuid.UUID
    my_role: Literal["owner", "delegate", "creator_pending"]
    created_for: CreatedFor
    subject_name: str
    display_name: str | None
    status: ProfileStatus
    visibility: ProfileVisibility
    completion_percent: int
    primary_photo_url: str | None
    subject_consent_pending: bool


class MemberProfileOut(BaseModel):
    """What another member sees. Never includes DOB, phone, full name or hidden fields."""

    id: uuid.UUID
    display_name: str
    age: int | None
    gender: Gender | None
    marital_status: MaritalStatus | None
    has_children: bool | None
    height_cm: int | None
    mother_tongue: SpokenLanguage | None
    current_country: str | None
    state: PlaceOut | None
    district: PlaceOut | None
    city: PlaceOut | None
    community_label: PlaceOut | None
    sub_community_label: PlaceOut | None
    qualification: EducationLevel | None
    field_of_study: FieldOfStudy | None
    institution: str | None
    employment_type: EmploymentType | None
    occupation: str | None
    industry: Industry | None
    employer: str | None
    income_band: IncomeBand | None
    family: FamilyIn | None
    native_district: PlaceOut | None
    lifestyle: LifestyleIn | None
    photos: list[PhotoOut]
    created_for: CreatedFor
