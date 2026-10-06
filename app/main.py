from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from app.api.router import api_router
from app.core.auth_error import AuthError
from app.core.error_handlers import (
    auth_error_handler,
    database_error_handler,
    http_error_handler,
    internal_error_handler,
    validation_error_handler,
)
from app.core.security_middleware import SecurityMiddleware
from app.core.settings import Settings
from app.database.database import Database
from app.services.password_service import PasswordService
from app.services.rate_limit_service import RateLimitService
from app.services.token_service import TokenService


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application without starting external services."""
    settings = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        database = Database(settings)
        app.state.database = database
        app.state.rate_limiter = RateLimitService(database, settings)
        try:
            yield
        finally:
            database.dispose()

    app = FastAPI(title="Cognova API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.passwords = PasswordService()
    app.state.tokens = TokenService(settings)
    app.add_exception_handler(AuthError, auth_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(HTTPException, http_error_handler)
    app.add_exception_handler(SQLAlchemyError, database_error_handler)
    app.add_exception_handler(Exception, internal_error_handler)
    app.add_middleware(
        SecurityMiddleware, production=settings.environment == "production"
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    )
    app.include_router(api_router)
    return app
