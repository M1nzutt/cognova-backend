import json
import logging
from time import perf_counter
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("cognova.requests")


class SecurityMiddleware:
    """Bound request bodies; emit headers and metadata-only request logs."""

    def __init__(self, app: ASGIApp, production: bool = False) -> None:
        self.app = app
        self.production = production

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(uuid4())
        started, status = perf_counter(), 500
        response_started = False

        async def safe_send(message: Message) -> None:
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                status = message["status"]
                response_started = True
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                headers["X-Content-Type-Options"] = "nosniff"
                headers["Referrer-Policy"] = "no-referrer"
                headers["X-Frame-Options"] = "DENY"
                if scope["path"].startswith("/api/"):
                    headers["Content-Security-Policy"] = (
                        "default-src 'none'; frame-ancestors 'none'"
                    )
                    headers["Cache-Control"] = "no-store"
                if self.production:
                    headers["Strict-Transport-Security"] = "max-age=31536000"
            await send(message)

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > 1048576:
                await JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "code": "PAYLOAD_TOO_LARGE",
                            "message": "La solicitud es demasiado grande.",
                        }
                    },
                )(scope, receive, safe_send)
                return
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        try:
            await self.app(scope, replay, safe_send)
        except Exception as exc:
            logger.error(
                json.dumps(
                    {
                        "event": "request_failed",
                        "request_id": request_id,
                        "exception_type": type(exc).__name__,
                    }
                )
            )
            if response_started:
                raise RuntimeError("Response transmission failed") from None
            await JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Ocurrió un error interno.",
                    }
                },
            )(scope, replay, safe_send)
        finally:
            route = getattr(scope.get("route"), "path", "unmatched")
            logger.info(
                json.dumps(
                    {
                        "event": "http_request",
                        "request_id": request_id,
                        "route": route,
                        "method": scope["method"],
                        "status": status,
                        "duration_ms": round((perf_counter() - started) * 1000, 2),
                    }
                )
            )
