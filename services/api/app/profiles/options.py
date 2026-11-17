"""Closed option lists for profile and preference fields.

Codes are stored in the database and translated by the clients (packages/localization,
`options.<group>.<code>`). Adding a code is a data change in clients + here; removing one
needs a migration of existing rows.
"""

from enum import StrEnum


class CreatedFor(StrEnum):
    SELF = "self"
    SON = "son"
    DAUGHTER = "daughter"
    BROTHER = "brother"
    SISTER = "sister"
    RELATIVE = "relative"
    FRIEND = "friend"


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"


class MaritalStatus(StrEnum):
    NEVER_MARRIED = "never_married"
    DIVORCED = "divorced"
    WIDOWED = "widowed"
    AWAITING_DIVORCE = "awaiting_divorce"


class PhysicalStatus(StrEnum):
    NORMAL = "normal"
    PHYSICALLY_CHALLENGED = "physically_challenged"


class SpokenLanguage(StrEnum):
    TAMIL = "tamil"
    ENGLISH = "english"
    TELUGU = "telugu"
    KANNADA = "kannada"
    MALAYALAM = "malayalam"
    HINDI = "hindi"
    SAURASHTRA = "saurashtra"
    OTHER = "other"


class Diet(StrEnum):
    VEGETARIAN = "vegetarian"
    NON_VEGETARIAN = "non_vegetarian"
    EGGETARIAN = "eggetarian"
    VEGAN = "vegan"


class Habit(StrEnum):
    NO = "no"
    OCCASIONALLY = "occasionally"
    YES = "yes"


class FamilyType(StrEnum):
    NUCLEAR = "nuclear"
    JOINT = "joint"


class FamilyValues(StrEnum):
    TRADITIONAL = "traditional"
    MODERATE = "moderate"
    LIBERAL = "liberal"


class EducationLevel(StrEnum):
    SECONDARY = "secondary"
    HIGHER_SECONDARY = "higher_secondary"
    DIPLOMA = "diploma"
    BACHELORS = "bachelors"
    MASTERS = "masters"
    DOCTORATE = "doctorate"
    OTHER = "other"


class FieldOfStudy(StrEnum):
    ENGINEERING = "engineering"
    MEDICINE = "medicine"
    SCIENCE = "science"
    COMMERCE = "commerce"
    ARTS = "arts"
    LAW = "law"
    MANAGEMENT = "management"
    COMPUTER_APPLICATIONS = "computer_applications"
    EDUCATION = "education"
    OTHER = "other"


class EmploymentType(StrEnum):
    PRIVATE = "private"
    GOVERNMENT = "government"
    BUSINESS = "business"
    SELF_EMPLOYED = "self_employed"
    NOT_WORKING = "not_working"
    STUDENT = "student"


class Industry(StrEnum):
    IT_SOFTWARE = "it_software"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    FINANCE = "finance"
    GOVERNMENT = "government"
    MANUFACTURING = "manufacturing"
    AGRICULTURE = "agriculture"
    TRADE = "trade"
    OTHER = "other"


class IncomeBand(StrEnum):
    """Annual income in INR. Optional and privacy-controlled (PRD §4.2)."""

    LT_3L = "lt_3l"
    L3_5 = "3_5l"
    L5_10 = "5_10l"
    L10_20 = "10_20l"
    L20_50 = "20_50l"
    GT_50L = "gt_50l"


class Interest(StrEnum):
    MUSIC = "music"
    READING = "reading"
    TRAVEL = "travel"
    COOKING = "cooking"
    SPORTS = "sports"
    MOVIES = "movies"
    ART = "art"
    TEMPLE_VISITS = "temple_visits"
    YOGA = "yoga"
    GARDENING = "gardening"
    PHOTOGRAPHY = "photography"
    DANCE = "dance"


class Visibility(StrEnum):
    """Who can see a field or photo, besides the owner and their delegates."""

    MEMBERS = "members"  # any approved member who can discover the profile
    CONNECTIONS = "connections"  # only after a mutually accepted interest (Phase 4)
    HIDDEN = "hidden"


class ProfileVisibility(StrEnum):
    DISCOVERABLE = "discoverable"
    PAUSED = "paused"


class ProfileStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    NEEDS_CHANGES = "needs_changes"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class ModerationStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReviewReason(StrEnum):
    """Moderator reason codes shown (translated) to the member."""

    INCOMPLETE = "incomplete"
    PHOTO_UNCLEAR = "photo_unclear"
    PHOTO_NOT_PERSON = "photo_not_person"
    CONTACT_IN_TEXT = "contact_in_text"
    INAPPROPRIATE_TEXT = "inappropriate_text"
    INCONSISTENT_DETAILS = "inconsistent_details"
    COMMUNITY_ELIGIBILITY = "community_eligibility"
    OTHER = "other"


ALL_OPTIONS: dict[str, type[StrEnum]] = {
    "created_for": CreatedFor,
    "gender": Gender,
    "marital_status": MaritalStatus,
    "physical_status": PhysicalStatus,
    "language": SpokenLanguage,
    "diet": Diet,
    "habit": Habit,
    "family_type": FamilyType,
    "family_values": FamilyValues,
    "education_level": EducationLevel,
    "field_of_study": FieldOfStudy,
    "employment_type": EmploymentType,
    "industry": Industry,
    "income_band": IncomeBand,
    "interest": Interest,
    "visibility": Visibility,
    "review_reason": ReviewReason,
}

MIN_AGE = 18
MIN_HEIGHT_CM = 120
MAX_HEIGHT_CM = 220
