"""SMS provider adapter. Production providers (e.g. MSG91) plug in behind `SmsProvider`."""

import logging
from typing import Protocol

from app.common.config import get_settings
from app.common.phone import mask_phone

log = logging.getLogger("vaibhav.sms")


class SmsProvider(Protocol):
    async def send_otp(self, phone_e164: str, code: str, language: str) -> None: ...


class ConsoleSmsProvider:
    """Development provider: logs the OTP instead of sending it."""

    async def send_otp(self, phone_e164: str, code: str, language: str) -> None:
        if get_settings().env in ("staging", "production"):
            raise RuntimeError("Console SMS provider cannot be used in staging/production")
        log.warning("DEV OTP for %s (%s): %s", mask_phone(phone_e164), language, code)


def get_sms_provider() -> SmsProvider:
    provider = get_settings().sms_provider
    if provider == "console":
        return ConsoleSmsProvider()
    raise RuntimeError(f"Unknown SMS provider {provider!r}")
