import logging
import re
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.admin.router import router as admin_router
from app.auth.router import router as auth_router
from app.common.config import get_settings
from app.common.errors import install_error_handlers
from app.common.redis import close_redis
from app.consent.router import router as consent_router
from app.database import models  # noqa: F401  (register all mappers)
from app.database.session import dispose_engine
from app.delegation.router import router as delegation_router
from app.health.router import router as health_router
from app.media import storage
from app.media.router import router as media_router
from app.moderation.router import router as moderation_router
from app.preferences.router import router as preferences_router
from app.profiles.router import router as profiles_router
from app.reference.router import router as reference_router
from app.users.router import router as users_router

API_PREFIX = "/api/v1"
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.storage_create_bucket and settings.env in ("local", "test", "development"):
        try:
            await storage.ensure_bucket()
        except Exception:  # storage may start after the API in docker-compose
            logging.getLogger("vaibhav").warning("Could not ensure storage bucket at startup")
    yield
    await dispose_engine()
    await close_redis()


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    is_prod = settings.env in ("staging", "production")

    app = FastAPI(
        title="VAIBHAV API",
        version="0.1.0",
        description="VAIBHAV Tamil matrimony platform API.",
        lifespan=lifespan,
        docs_url=None if is_prod else "/docs",
        redoc_url=None,
        openapi_url=None if is_prod else "/openapi.json",
    )
    install_error_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
        max_age=600,
    )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if _REQUEST_ID.match(incoming) else uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers.setdefault("Cache-Control", "no-store")
        if is_prod:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response

    app.include_router(health_router)
    for router in (
        auth_router,
        users_router,
        consent_router,
        reference_router,
        profiles_router,
        delegation_router,
        preferences_router,
        media_router,
        moderation_router,
        admin_router,
    ):
        app.include_router(router, prefix=API_PREFIX)
    return app


app = create_app()
