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
    args = parser.parse_args()
    if args.cmd == "grant-role":
        asyncio.run(grant_role(args.phone, args.role))
    elif args.cmd == "export-openapi":
        export_openapi()


if __name__ == "__main__":
    main()
