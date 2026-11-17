from enum import StrEnum


class RoleCode(StrEnum):
    """Privileged roles (PRD §9.1). Ordinary members hold no role."""

    SUPER_ADMIN = "super_admin"
    OPERATIONS_ADMIN = "operations_admin"
    VERIFICATION_OPERATOR = "verification_operator"
    MODERATOR = "moderator"
    SUPPORT = "support"
    CONTENT_MANAGER = "content_manager"
    ANALYST = "analyst"


ROLE_DEFINITIONS: dict[RoleCode, tuple[str, str]] = {
    RoleCode.SUPER_ADMIN: ("Super Admin", "Platform configuration and role management"),
    RoleCode.OPERATIONS_ADMIN: ("Operations Admin", "User/profile lifecycle and queue oversight"),
    RoleCode.VERIFICATION_OPERATOR: ("Verification Operator", "Verification queue and evidence"),
    RoleCode.MODERATOR: ("Moderator", "Reports and content moderation"),
    RoleCode.SUPPORT: ("Customer Support", "Tickets and limited account metadata"),
    RoleCode.CONTENT_MANAGER: ("Content Manager", "Localized CMS content only"),
    RoleCode.ANALYST: ("Analyst", "Aggregated, de-identified reports only"),
}
