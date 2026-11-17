from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "test", "development", "staging", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VAIBHAV_", env_file=".env", extra="ignore")

    env: Environment = "local"
    app_name: str = "VAIBHAV"

    database_url: str = "mysql+asyncmy://vaibhav:vaibhav@127.0.0.1:3306/vaibhav?charset=utf8mb4"
    redis_url: str = "redis://127.0.0.1:6379/0"

    # Comma-separated origins allowed to call the API directly from a browser.
    cors_origins: str = "http://localhost:3000"

    jwt_secret: SecretStr = SecretStr("dev-only-insecure-jwt-secret-change-me-0000")
    jwt_issuer: str = "vaibhav-api"
    access_token_ttl_seconds: int = 15 * 60
    refresh_token_ttl_seconds: int = 30 * 24 * 3600

    # Keyed hash for OTP codes and refresh tokens at rest.
    hash_pepper: SecretStr = SecretStr("dev-only-insecure-pepper-change-me-0000000")

    otp_length: int = 6
    otp_ttl_seconds: int = 300
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 30
    otp_max_requests_per_phone_per_hour: int = 5
    otp_max_requests_per_ip_per_hour: int = 30
    # Development convenience: echo the OTP in the API response. Refused in staging/production.
    otp_debug_echo: bool = False
    sms_provider: Literal["console"] = "console"

    default_phone_region: str = "IN"
    terms_policy_version: str = "2026-11-draft"
    privacy_policy_version: str = "2026-11-draft"

    trusted_proxy_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _guard_production(self) -> "Settings":
        if self.env in ("staging", "production"):
            if self.otp_debug_echo:
                raise ValueError("otp_debug_echo must be disabled in staging/production")
            for name in ("jwt_secret", "hash_pepper"):
                value: SecretStr = getattr(self, name)
                if "dev-only" in value.get_secret_value() or len(value.get_secret_value()) < 32:
                    raise ValueError(f"{name} must be set to a strong secret outside local/test")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
