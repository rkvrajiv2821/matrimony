import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.users.models import Language
from app.users.schemas import MeOut


class OtpRequestIn(BaseModel):
    phone: str = Field(min_length=1, max_length=20, examples=["+919876543210"])
    language: Language = Language.EN


class OtpChallengeOut(BaseModel):
    challenge_id: str
    expires_in: int
    resend_after: int
    phone_masked: str
    # Present only when VAIBHAV_OTP_DEBUG_ECHO is on (local/test). Never in staging/production.
    debug_code: str | None = None


class OtpResendIn(BaseModel):
    challenge_id: str = Field(max_length=64)


class ConsentChoices(BaseModel):
    terms: bool = False
    privacy: bool = False
    marketing: bool | None = None


class OtpVerifyIn(BaseModel):
    challenge_id: str = Field(max_length=64)
    code: str = Field(pattern=r"^\d{4,8}$")
    consents: ConsentChoices | None = None
    language: Language | None = None
    device_id: str | None = Field(default=None, max_length=100)
    device_label: str | None = Field(default=None, max_length=150)


class TokenPairOut(BaseModel):
    access_token: str
    access_token_expires_in: int
    refresh_token: str
    refresh_token_expires_at: datetime
    token_type: str = "bearer"  # noqa: S105


class AuthResultOut(TokenPairOut):
    is_new_user: bool
    user: MeOut


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=200)


class LogoutIn(BaseModel):
    all_devices: bool = False


class SessionOut(BaseModel):
    id: uuid.UUID
    device_label: str | None
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime
    current: bool
