from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.core.auth_error import AuthError


def error_response(
    status: int, code: str, message: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message}},
        headers=headers,
    )


async def auth_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AuthError)
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else {}
    if exc.status_code == 429:
        headers["Retry-After"] = str(
            request.app.state.settings.auth_rate_window_seconds
        )
    return error_response(exc.status_code, exc.code, exc.message, headers)


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Never serialize input values, including passwords, from validation errors.
    return error_response(
        422, "VALIDATION_ERROR", "Hay datos inválidos en el formulario."
    )


async def http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    return error_response(exc.status_code, "HTTP_ERROR", "Solicitud no válida.")


async def database_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return error_response(
        503, "SERVICE_UNAVAILABLE", "Servicio temporalmente no disponible."
    )


async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return error_response(500, "INTERNAL_ERROR", "Ocurrió un error interno.")
