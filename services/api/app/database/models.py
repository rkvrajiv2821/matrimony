"""Imports every model so Alembic and the mapper registry see the full schema."""

from app.audit.models import AuditLog
from app.auth.models import UserSession
from app.consent.models import Consent
from app.database.base import Base
from app.entitlements.models import Plan, PlanEntitlement, PlanVersion, UserEntitlement
from app.flags.models import FeatureFlag, SystemSetting
from app.users.models import Role, User, UserRole

__all__ = [
    "AuditLog",
    "Base",
    "Consent",
    "FeatureFlag",
    "Plan",
    "PlanEntitlement",
    "PlanVersion",
    "Role",
    "SystemSetting",
    "User",
    "UserEntitlement",
    "UserRole",
    "UserSession",
]
