"""Phase 1 admin endpoints: feature flags and audit log viewer.

Admin MFA and the admin portal arrive in Phase 5; until then these are reachable only by
users granted a role through the CLI (`python -m app.cli grant-role`).
"""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.audit import service as audit
from app.audit.models import AuditLog
from app.common.errors import NotFound
from app.flags.models import FeatureFlag
from app.security.deps import DB, AuthContext, Meta, require_roles
from app.security.roles import RoleCode

router = APIRouter(prefix="/admin", tags=["admin"])

SuperAdmin = Annotated[AuthContext, Depends(require_roles(RoleCode.SUPER_ADMIN))]
AuditReader = Annotated[AuthContext, Depends(require_roles(RoleCode.OPERATIONS_ADMIN))]


class FlagOut(BaseModel):
    key: str
    enabled: bool
    rollout_percent: int
    description: str
    config: dict[str, Any] | None
    updated_at: datetime


class FlagPatchIn(BaseModel):
    enabled: bool | None = None
    rollout_percent: int | None = Field(default=None, ge=0, le=100)
    config: dict[str, Any] | None = None


def _flag_out(f: FeatureFlag) -> FlagOut:
    return FlagOut(
        key=f.key,
        enabled=f.enabled,
        rollout_percent=f.rollout_percent,
        description=f.description,
        config=f.config_json,
        updated_at=f.updated_at,
    )


@router.get("/feature-flags", response_model=list[FlagOut])
async def list_flags(_: SuperAdmin, db: DB) -> list[FlagOut]:
    return [_flag_out(f) for f in await db.scalars(select(FeatureFlag).order_by(FeatureFlag.key))]


@router.patch("/feature-flags/{key}", response_model=FlagOut)
async def patch_flag(key: str, body: FlagPatchIn, auth: SuperAdmin, db: DB, meta: Meta) -> FlagOut:
    flag = await db.get(FeatureFlag, key, with_for_update=True)
    if flag is None:
        raise NotFound()
    before = {"enabled": flag.enabled, "rollout_percent": flag.rollout_percent}
    if body.enabled is not None:
        flag.enabled = body.enabled
    if body.rollout_percent is not None:
        flag.rollout_percent = body.rollout_percent
    if "config" in body.model_fields_set:
        flag.config_json = body.config
    flag.updated_by = auth.user.id
    await audit.record(
        db,
        action="feature_flag.update",
        resource_type="feature_flag",
        resource_id=key,
        actor_user_id=auth.user.id,
        before=before,
        after={"enabled": flag.enabled, "rollout_percent": flag.rollout_percent},
        ip_hash=meta.ip_hash,
        request_id=meta.request_id,
    )
    await db.flush()
    await db.refresh(flag)
    return _flag_out(flag)


class AuditOut(BaseModel):
    id: int
    action: str
    resource_type: str
    resource_id: str | None
    actor_user_id: int | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    request_id: str | None
    created_at: datetime


class AuditPage(BaseModel):
    items: list[AuditOut]
    next_cursor: int | None


@router.get("/audit-logs", response_model=AuditPage)
async def list_audit_logs(
    _: AuditReader,
    db: DB,
    cursor: Annotated[int | None, Query(description="Return entries with id < cursor")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    action: str | None = None,
    resource_type: str | None = None,
) -> AuditPage:
    stmt = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit + 1)
    if cursor is not None:
        stmt = stmt.where(AuditLog.id < cursor)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    rows = list(await db.scalars(stmt))
    page, more = rows[:limit], len(rows) > limit
    return AuditPage(
        items=[
            AuditOut(
                id=r.id,
                action=r.action,
                resource_type=r.resource_type,
                resource_id=r.resource_id,
                actor_user_id=r.actor_user_id,
                before=r.before_json,
                after=r.after_json,
                request_id=r.request_id,
                created_at=r.created_at,
            )
            for r in page
        ],
        next_cursor=page[-1].id if more and page else None,
    )
