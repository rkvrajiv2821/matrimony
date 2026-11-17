import hashlib
import hmac

from fastapi import Request

from app.common.config import get_settings


def client_ip(request: Request) -> str:
    """Client IP, honouring X-Forwarded-For only for the configured number of trusted proxies."""
    settings = get_settings()
    if settings.trusted_proxy_count > 0:
        forwarded = request.headers.get("x-forwarded-for", "")
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if len(parts) >= settings.trusted_proxy_count:
            return parts[-settings.trusted_proxy_count]
    return request.client.host if request.client else "unknown"


def ip_hash(ip: str) -> str:
    """Keyed hash so raw IPs are never stored."""
    pepper = get_settings().hash_pepper.get_secret_value().encode()
    return hmac.new(pepper, f"ip:{ip}".encode(), hashlib.sha256).hexdigest()
