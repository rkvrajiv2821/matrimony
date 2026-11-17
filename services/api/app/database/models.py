"""Imports every model so Alembic and the mapper registry see the full schema."""

from app.audit.models import AuditLog
from app.auth.models import UserSession
from app.consent.models import Consent
from app.database.base import Base
from app.delegation.models import DelegatedAccess
from app.entitlements.models import Plan, PlanEntitlement, PlanVersion, UserEntitlement
from app.flags.models import FeatureFlag, SystemSetting
from app.media.models import ProfilePhoto
from app.preferences.models import PartnerPreference, PreferenceCommunityValue
from app.profiles.models import (
    Profile,
    ProfileCommunity,
    ProfileEducation,
    ProfileEmployment,
    ProfileFamilyDetails,
    ProfilePersonalDetails,
    ProfileStatusHistory,
)
from app.reference.models import CommunityTaxonomy, Location
from app.users.models import Role, User, UserRole

__all__ = [
    "AuditLog",
    "Base",
    "CommunityTaxonomy",
    "Consent",
    "DelegatedAccess",
    "FeatureFlag",
    "Location",
    "PartnerPreference",
    "Plan",
    "PlanEntitlement",
    "PlanVersion",
    "PreferenceCommunityValue",
    "Profile",
    "ProfileCommunity",
    "ProfileEducation",
    "ProfileEmployment",
    "ProfileFamilyDetails",
    "ProfilePersonalDetails",
    "ProfilePhoto",
    "ProfileStatusHistory",
    "Role",
    "SystemSetting",
    "User",
    "UserEntitlement",
    "UserRole",
    "UserSession",
]
