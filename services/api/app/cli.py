"""Operator CLI.

uv run python -m app.cli grant-role +919876543210 super_admin
uv run python -m app.cli export-openapi > ../../packages/api-client/openapi.json
"""

import argparse
import asyncio
import json
import sys

from sqlalchemy import select

from app.audit import service as audit
from app.common.phone import normalize_phone
from app.database.session import dispose_engine, get_sessionmaker
from app.security.roles import RoleCode
from app.users.models import Role, User, UserRole


async def grant_role(phone: str, role_code: str) -> None:
    async with get_sessionmaker()() as db:
        user = await db.scalar(select(User).where(User.phone_e164 == normalize_phone(phone)))
        if user is None:
            sys.exit("No user with that phone. They must register first.")
        role = await db.scalar(select(Role).where(Role.code == role_code))
        if role is None:
            sys.exit(f"Unknown role {role_code!r}")
        if await db.get(UserRole, (user.id, role.id)) is None:
            db.add(UserRole(user_id=user.id, role_id=role.id))
            await audit.record(
                db,
                action="role.grant",
                resource_type="user",
                resource_id=str(user.public_id),
                after={"role": role_code, "via": "cli"},
            )
        await db.commit()
    await dispose_engine()
    print(f"Granted {role_code}")


async def moderation_queue() -> None:
    from app.profiles.models import Profile
    from app.profiles.options import ProfileStatus

    async with get_sessionmaker()() as db:
        rows = await db.scalars(
            select(Profile)
            .where(Profile.profile_status == ProfileStatus.SUBMITTED)
            .order_by(Profile.submitted_at)
        )
        for p in rows:
            print(f"{p.public_id}  {p.display_name or '-':<30} submitted {p.submitted_at}")
    await dispose_engine()


async def approve_profile(profile_id: str) -> None:
    """Local/dev shortcut: approve a submitted profile and all its pending photos."""
    import uuid

    from app.common.time import utcnow
    from app.media.models import ProfilePhoto
    from app.profiles import service
    from app.profiles.models import Profile
    from app.profiles.options import ModerationStatus, ProfileStatus

    async with get_sessionmaker()() as db:
        profile = await db.scalar(
            select(Profile).where(Profile.public_id == uuid.UUID(profile_id)).with_for_update()
        )
        if profile is None or profile.profile_status != ProfileStatus.SUBMITTED:
            sys.exit("No submitted profile with that id.")
        photos = await db.scalars(
            select(ProfilePhoto).where(
                ProfilePhoto.profile_id == profile.id,
                ProfilePhoto.deleted_at.is_(None),
                ProfilePhoto.moderation_status == ModerationStatus.PENDING,
            )
        )
        for photo in photos:
            photo.moderation_status = ModerationStatus.APPROVED
        await service.transition(
            db,
            profile,
            ProfileStatus.APPROVED,
            by="moderator",
            actor=None,
            meta=None,
            note=f"approved via CLI at {utcnow().isoformat()}",
        )
        await db.commit()
    await dispose_engine()
    print("Approved")


def export_openapi() -> None:
    from app.main import app

    print(json.dumps(app.openapi(), indent=2, ensure_ascii=False, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("grant-role")
    g.add_argument("phone")
    g.add_argument("role", choices=[r.value for r in RoleCode])
    sub.add_parser("export-openapi")
    sub.add_parser("moderation-queue")
    a = sub.add_parser("approve-profile")
    a.add_argument("profile_id")
    args = parser.parse_args()
    if args.cmd == "grant-role":
        asyncio.run(grant_role(args.phone, args.role))
    elif args.cmd == "export-openapi":
        export_openapi()
    elif args.cmd == "moderation-queue":
        asyncio.run(moderation_queue())
    elif args.cmd == "approve-profile":
        asyncio.run(approve_profile(args.profile_id))


if __name__ == "__main__":
    main()
