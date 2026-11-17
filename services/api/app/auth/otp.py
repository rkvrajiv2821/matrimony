"""OTP challenges stored in Redis.

- Codes are stored only as keyed hashes.
- One active challenge per phone; a new request invalidates the previous one.
- Resend cooldown, per-phone and per-IP hourly caps, per-challenge attempt cap.
- Successful verification is single-use (atomic DEL).
"""

from dataclasses import dataclass

from app.common import ratelimit
from app.common.config import get_settings
from app.common.errors import AppError, RateLimited
from app.common.ids import uuid7
from app.common.redis import get_redis
from app.security.hashing import constant_time_equals, keyed_hash, new_otp


class OtpInvalid(AppError):
    code = "otp_invalid"
    message = "The code is incorrect or has expired."


@dataclass(frozen=True)
class IssuedChallenge:
    challenge_id: str
    code: str
    expires_in: int
    resend_after: int


@dataclass(frozen=True)
class VerifiedChallenge:
    challenge_id: str
    phone_e164: str


def _ch_key(challenge_id: str) -> str:
    return f"otp:ch:{challenge_id}"


def _phone_key(phone: str) -> str:
    return f"otp:phone:{phone}"


def _cooldown_key(phone: str) -> str:
    return f"otp:cooldown:{phone}"


async def _check_cooldown(phone: str) -> None:
    ttl = await get_redis().ttl(_cooldown_key(phone))
    if ttl and ttl > 0:
        raise RateLimited(
            retry_after=ttl,
            code="otp_cooldown",
            message="Please wait before requesting a new code.",
        )


async def _enforce_caps(phone: str, ip_hash: str) -> None:
    s = get_settings()
    await ratelimit.hit(
        "otp_phone", phone, limit=s.otp_max_requests_per_phone_per_hour, window_seconds=3600
    )
    await ratelimit.hit(
        "otp_ip", ip_hash, limit=s.otp_max_requests_per_ip_per_hour, window_seconds=3600
    )


async def issue(phone: str, ip_hash: str) -> IssuedChallenge:
    s = get_settings()
    await _check_cooldown(phone)
    await _enforce_caps(phone, ip_hash)

    redis = get_redis()
    challenge_id = str(uuid7())
    code = new_otp(s.otp_length)
    previous = await redis.get(_phone_key(phone))
    previous = str(previous) if previous else None

    pipe = redis.pipeline(transaction=True)
    if previous:
        pipe.delete(_ch_key(previous))
    pipe.hset(
        _ch_key(challenge_id),
        mapping={
            "phone": phone,
            "code_hash": keyed_hash("otp", f"{challenge_id}:{code}"),
            "attempts": 0,
        },
    )
    pipe.expire(_ch_key(challenge_id), s.otp_ttl_seconds)
    pipe.set(_phone_key(phone), challenge_id, ex=s.otp_ttl_seconds)
    pipe.set(_cooldown_key(phone), 1, ex=s.otp_resend_cooldown_seconds)
    await pipe.execute()
    return IssuedChallenge(challenge_id, code, s.otp_ttl_seconds, s.otp_resend_cooldown_seconds)


async def resend(challenge_id: str, ip_hash: str) -> tuple[str, IssuedChallenge]:
    """Issue a fresh code for the phone behind an existing challenge."""
    phone = await get_redis().hget(_ch_key(challenge_id), "phone")
    if not phone:
        raise OtpInvalid("This code has expired. Please start again.", code="otp_expired")
    return str(phone), await issue(str(phone), ip_hash)


async def peek(challenge_id: str, code: str) -> VerifiedChallenge:
    """Check a code without consuming the challenge. Counts as an attempt."""
    s = get_settings()
    redis = get_redis()
    key = _ch_key(challenge_id)
    data = await redis.hgetall(key)
    if not data:
        raise OtpInvalid("This code has expired. Please request a new one.", code="otp_expired")
    attempts = int(await redis.hincrby(key, "attempts", 1))
    if attempts > s.otp_max_attempts:
        await redis.delete(key)
        raise OtpInvalid(
            "Too many incorrect attempts. Please request a new code.", code="otp_too_many_attempts"
        )
    expected = str(data["code_hash"])
    if not constant_time_equals(expected, keyed_hash("otp", f"{challenge_id}:{code}")):
        raise OtpInvalid(details={"attempts_remaining": s.otp_max_attempts - attempts})
    # Correct code: refund the attempt so a follow-up (e.g. adding consent) is not penalised.
    await redis.hincrby(key, "attempts", -1)
    return VerifiedChallenge(challenge_id, str(data["phone"]))


async def consume(verified: VerifiedChallenge) -> None:
    """Single-use: only the first caller to delete the challenge succeeds."""
    redis = get_redis()
    deleted = await redis.delete(_ch_key(verified.challenge_id))
    if deleted != 1:
        raise OtpInvalid("This code has already been used.", code="otp_expired")
    current = await redis.get(_phone_key(verified.phone_e164))
    if current == verified.challenge_id:
        await redis.delete(_phone_key(verified.phone_e164))
