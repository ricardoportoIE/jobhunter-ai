"""Bound request bytes before JSON parsing; private API responses never enter caches."""

import logging
from uuid import uuid4

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestBoundary:
    def __init__(self, app: ASGIApp, maximum_bytes: int = 131072) -> None:
        self.app, self.maximum_bytes = app, maximum_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        correlation = str(uuid4())
        scope.setdefault("state", {})["correlation_id"] = correlation
        chunks = bytearray()
        maximum = (
            4 * 1024 * 1024
            if scope.get("path") == "/api/v1/candidate/cv/extract"
            else self.maximum_bytes
        )
        if scope.get("method") == "PATCH" and scope.get("path", "").startswith(
            "/api/v1/candidate/cv/drafts/"
        ):
            maximum = 2 * 1024 * 1024
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunks.extend(message.get("body", b""))
            if len(chunks) > maximum:
                response = JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "code": "BODY_TOO_LARGE",
                            "message": "The request exceeds the allowed size.",
                            "correlation_id": correlation,
                        }
                    },
                )
                await response(scope, receive, send)
                return
            if not message.get("more_body", False):
                break
        sent = False
        started = False

        async def replay() -> Message:
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": bytes(chunks), "more_body": False}
            return await receive()

        async def headers(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                values = list(message.get("headers", []))
                values = [(k, v) for k, v in values if k not in {b"cache-control", b"x-request-id"}]
                values.extend(
                    [
                        (b"cache-control", b"no-store"),
                        (b"x-request-id", correlation.encode()),
                        (b"x-content-type-options", b"nosniff"),
                    ]
                )
                message["headers"] = values
            await send(message)

        try:
            await self.app(scope, replay, headers)
        except Exception as error:
            logging.getLogger(__name__).error(
                "request_failed correlation=%s type=%s", correlation, type(error).__name__
            )
            if not started:
                response = JSONResponse(
                    status_code=500,
                    content={
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": "Could not complete the operation.",
                            "correlation_id": correlation,
                        }
                    },
                )
                await response(scope, replay, headers)
