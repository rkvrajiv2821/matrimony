import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.common.phone import mask_phone
from app.users.models import Language, User


class MeOut(BaseModel):
    id: uuid.UUID
    phone_masked: str
    phone_verified: bool
    email: str | None
    email_verified: bool
    status: str
    preferred_language: Language
    roles: list[str]
    created_at: datetime

    @classmethod
    def from_user(cls, user: User) -> "MeOut":
        return cls(
            id=user.public_id,
            phone_masked=mask_phone(user.phone_e164),
            phone_verified=user.phone_verified_at is not None,
            email=user.email,
            email_verified=user.email_verified_at is not None,
            status=user.status,
            preferred_language=Language(user.preferred_language),
            roles=sorted(user.role_codes),
            created_at=user.created_at,
        )


class MePatchIn(BaseModel):
    preferred_language: Language | None = None
    email: EmailStr | None = None
