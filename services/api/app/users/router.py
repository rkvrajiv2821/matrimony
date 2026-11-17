from fastapi import APIRouter
from sqlalchemy import select

from app.audit import service as audit
from app.common.errors import Conflict
from app.security.deps import DB, Auth, Meta
from app.users.models import User
from app.users.schemas import MeOut, MePatchIn

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=MeOut)
async def get_me(auth: Auth) -> MeOut:
    return MeOut.from_user(auth.user)


@router.patch("/me", response_model=MeOut)
async def patch_me(body: MePatchIn, auth: Auth, db: DB, meta: Meta) -> MeOut:
    user = auth.user
    changes = body.model_dump(exclude_unset=True)
    before: dict[str, object] = {}
    after: dict[str, object] = {}

    if "preferred_language" in changes and body.preferred_language is not None:
        before["preferred_language"] = user.preferred_language
        user.preferred_language = body.preferred_language.value
        after["preferred_language"] = user.preferred_language

    if "email" in changes:
        email = body.email.lower() if body.email else None
        if email != user.email:
            if email and await db.scalar(select(User.id).where(User.email == email)):
                raise Conflict("This email is already in use.", code="email_taken")
            before["email_set"] = user.email is not None
            user.email = email
            user.email_verified_at = None  # verification flow arrives with the email provider
            after["email_set"] = email is not None

    if after:
        await audit.record(
            db,
            action="user.update",
            resource_type="user",
            resource_id=str(user.public_id),
            actor_user_id=user.id,
            before=before,
            after=after,
            ip_hash=meta.ip_hash,
            request_id=meta.request_id,
        )
    await db.flush()
    return MeOut.from_user(user)
