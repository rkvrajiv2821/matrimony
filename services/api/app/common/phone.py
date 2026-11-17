import phonenumbers

from app.common.config import get_settings
from app.common.errors import AppError


class InvalidPhone(AppError):
    status_code = 422
    code = "invalid_phone"
    message = "Enter a valid mobile number."


def normalize_phone(raw: str) -> str:
    """Return the canonical E.164 form of a mobile number or raise InvalidPhone."""
    try:
        parsed = phonenumbers.parse(raw, get_settings().default_phone_region)
    except phonenumbers.NumberParseException as exc:
        raise InvalidPhone() from exc
    if not phonenumbers.is_valid_number(parsed):
        raise InvalidPhone()
    if phonenumbers.number_type(parsed) not in (
        phonenumbers.PhoneNumberType.MOBILE,
        phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE,
    ):
        raise InvalidPhone()
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def mask_phone(e164: str) -> str:
    """+919876543210 -> +91******3210"""
    if len(e164) <= 7:
        return "*" * len(e164)
    return e164[:3] + "*" * (len(e164) - 7) + e164[-4:]
