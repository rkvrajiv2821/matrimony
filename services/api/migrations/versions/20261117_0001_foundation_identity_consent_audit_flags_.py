"""foundation: identity, consent, audit, flags, entitlements

Revision ID: 0001
Revises:
Create Date: 2026-11-17 10:03:08.207428
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

DT = sa.DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql")

ROLES = [
    ("super_admin", "Super Admin", "Platform configuration and role management"),
    ("operations_admin", "Operations Admin", "User/profile lifecycle and queue oversight"),
    ("verification_operator", "Verification Operator", "Verification queue and evidence"),
    ("moderator", "Moderator", "Reports and content moderation"),
    ("support", "Customer Support", "Tickets and limited account metadata"),
    ("content_manager", "Content Manager", "Localized CMS content only"),
    ("analyst", "Analyst", "Aggregated, de-identified reports only"),
]

FLAGS = [
    ("monetization_enabled", "PRD v1.1: paid plans and checkout. Must stay OFF for free launch."),
]

FREE_ENTITLEMENTS = [
    "profile.create",
    "search.use",
    "recommendations.view",
    "shortlist.use",
    "interests.send",
    "messaging.send",
    "horoscope.details",
]

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", DT, nullable=False),
        sa.Column("updated_at", DT, nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plans")),
        sa.UniqueConstraint("code", name=op.f("uq_plans_code")),
    )
    op.create_table(
        "roles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roles")),
        sa.UniqueConstraint("code", name=op.f("uq_roles_code")),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("phone_e164", sa.String(length=16), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("preferred_language", sa.String(length=10), nullable=False),
        sa.Column("phone_verified_at", DT, nullable=True),
        sa.Column("email_verified_at", DT, nullable=True),
        sa.Column("last_login_at", DT, nullable=True),
        sa.Column("created_at", DT, nullable=False),
        sa.Column("updated_at", DT, nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
        sa.UniqueConstraint("phone_e164", name=op.f("uq_users_phone_e164")),
        sa.UniqueConstraint("public_id", name=op.f("uq_users_public_id")),
    )
    op.create_index(op.f("ix_users_status"), "users", ["status"], unique=False)
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("actor_user_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("before_json", sa.JSON(), nullable=True),
        sa.Column("after_json", sa.JSON(), nullable=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", DT, nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_audit_logs_actor_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_index(
        "ix_audit_logs_actor_created", "audit_logs", ["actor_user_id", "created_at"], unique=False
    )
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False)
    op.create_index(
        "ix_audit_logs_resource", "audit_logs", ["resource_type", "resource_id"], unique=False
    )
    op.create_table(
        "consents",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("consent_type", sa.String(length=30), nullable=False),
        sa.Column("policy_version", sa.String(length=30), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("granted_at", DT, nullable=False),
        sa.Column("withdrawn_at", DT, nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_consents_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_consents")),
        sa.UniqueConstraint("public_id", name=op.f("uq_consents_public_id")),
    )
    op.create_index(
        "ix_consents_user_type",
        "consents",
        ["user_id", "consent_type", "withdrawn_at"],
        unique=False,
    )
    op.create_table(
        "feature_flags",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("rollout_percent", sa.SmallInteger(), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", DT, nullable=False),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name=op.f("fk_feature_flags_updated_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_feature_flags")),
    )
    op.create_table(
        "plan_versions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("plan_id", sa.BigInteger(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=True),
        sa.Column("tax_config_json", sa.JSON(), nullable=True),
        sa.Column("effective_from", DT, nullable=False),
        sa.Column("effective_to", DT, nullable=True),
        sa.Column("created_at", DT, nullable=False),
        sa.Column("updated_at", DT, nullable=False),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["plans.id"],
            name=op.f("fk_plan_versions_plan_id_plans"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plan_versions")),
        sa.UniqueConstraint("plan_id", "version", name=op.f("uq_plan_versions_plan_id_version")),
    )
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", DT, nullable=False),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name=op.f("fk_system_settings_updated_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_system_settings")),
    )
    op.create_table(
        "user_entitlements",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("entitlement_key", sa.String(length=100), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("starts_at", DT, nullable=False),
        sa.Column("expires_at", DT, nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", DT, nullable=False),
        sa.Column("updated_at", DT, nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_entitlements_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_entitlements")),
    )
    op.create_index(
        "ix_user_entitlements_lookup",
        "user_entitlements",
        ["user_id", "status", "entitlement_key"],
        unique=False,
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("assigned_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", DT, nullable=False),
        sa.ForeignKeyConstraint(
            ["assigned_by"],
            ["users.id"],
            name=op.f("fk_user_roles_assigned_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], name=op.f("fk_user_roles_role_id_roles"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_user_roles_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "role_id", name=op.f("pk_user_roles")),
    )
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
        sa.Column("previous_refresh_token_hash", sa.String(length=64), nullable=True),
        sa.Column("device_id", sa.String(length=100), nullable=True),
        sa.Column("device_label", sa.String(length=150), nullable=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("last_used_at", DT, nullable=True),
        sa.Column("expires_at", DT, nullable=False),
        sa.Column("revoked_at", DT, nullable=True),
        sa.Column("revoked_reason", sa.String(length=50), nullable=True),
        sa.Column("created_at", DT, nullable=False),
        sa.Column("updated_at", DT, nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_sessions")),
        sa.UniqueConstraint("public_id", name=op.f("uq_user_sessions_public_id")),
        sa.UniqueConstraint("refresh_token_hash", name=op.f("uq_user_sessions_refresh_token_hash")),
    )
    op.create_index(
        op.f("ix_user_sessions_previous_refresh_token_hash"),
        "user_sessions",
        ["previous_refresh_token_hash"],
        unique=False,
    )
    op.create_index(
        "ix_user_sessions_user_active", "user_sessions", ["user_id", "revoked_at"], unique=False
    )
    op.create_table(
        "plan_entitlements",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("plan_version_id", sa.BigInteger(), nullable=False),
        sa.Column("entitlement_key", sa.String(length=100), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["plan_version_id"],
            ["plan_versions.id"],
            name=op.f("fk_plan_entitlements_plan_version_id_plan_versions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plan_entitlements")),
        sa.UniqueConstraint(
            "plan_version_id",
            "entitlement_key",
            name=op.f("uq_plan_entitlements_plan_version_id_entitlement_key"),
        ),
    )

    _seed()


def _seed() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    roles = sa.table("roles", sa.column("code"), sa.column("name"), sa.column("description"))
    op.bulk_insert(roles, [{"code": c, "name": n, "description": d} for c, n, d in ROLES])

    flags = sa.table(
        "feature_flags",
        sa.column("key"),
        sa.column("enabled"),
        sa.column("rollout_percent"),
        sa.column("description"),
        sa.column("updated_at"),
    )
    op.bulk_insert(
        flags,
        [
            {"key": k, "enabled": False, "rollout_percent": 0, "description": d, "updated_at": now}
            for k, d in FLAGS
        ],
    )

    plans = sa.table(
        "plans",
        sa.column("id"),
        sa.column("code"),
        sa.column("name"),
        sa.column("description"),
        sa.column("active"),
        sa.column("created_at"),
        sa.column("updated_at"),
    )
    op.bulk_insert(
        plans,
        [
            {
                "id": 1,
                "code": "free",
                "name": "Free",
                "description": "Every core VAIBHAV capability, free for all members.",
                "active": True,
                "created_at": now,
                "updated_at": now,
            }
        ],
    )
    versions = sa.table(
        "plan_versions",
        sa.column("id"),
        sa.column("plan_id"),
        sa.column("version"),
        sa.column("amount_minor"),
        sa.column("currency"),
        sa.column("duration_days"),
        sa.column("effective_from"),
        sa.column("created_at"),
        sa.column("updated_at"),
    )
    op.bulk_insert(
        versions,
        [
            {
                "id": 1,
                "plan_id": 1,
                "version": 1,
                "amount_minor": 0,
                "currency": "INR",
                "duration_days": None,
                "effective_from": datetime(2026, 1, 1),
                "created_at": now,
                "updated_at": now,
            }
        ],
    )
    ents = sa.table(
        "plan_entitlements",
        sa.column("plan_version_id"),
        sa.column("entitlement_key"),
        sa.column("value_json", sa.JSON),
    )
    op.bulk_insert(
        ents,
        [
            {"plan_version_id": 1, "entitlement_key": k, "value_json": True}
            for k in FREE_ENTITLEMENTS
        ],
    )


def downgrade() -> None:
    op.drop_table("plan_entitlements")
    op.drop_table("user_sessions")
    op.drop_table("user_roles")
    op.drop_table("user_entitlements")
    op.drop_table("system_settings")
    op.drop_table("plan_versions")
    op.drop_table("feature_flags")
    op.drop_table("consents")
    op.drop_table("audit_logs")
    op.drop_table("users")
    op.drop_table("roles")
    op.drop_table("plans")
