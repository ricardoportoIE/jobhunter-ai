"""Stable error envelopes omit request bodies, SQL and credentials."""

from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


class Problem(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        self.status, self.code, self.message = status, code, message


def failure(request: Request, status: int, code: str, message: str) -> JSONResponse:
    correlation = getattr(request.state, "correlation_id", str(uuid4()))
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "correlation_id": correlation,
            }
        },
        headers={"X-Request-ID": correlation, "Cache-Control": "no-store"},
    )


def install_errors(app: FastAPI) -> None:
    @app.exception_handler(Problem)
    async def problem(request: Request, error: Problem) -> JSONResponse:
        return failure(request, error.status, error.code, error.message)

    @app.exception_handler(RequestValidationError)
    async def validation(request: Request, error: RequestValidationError) -> JSONResponse:
        return failure(request, 422, "INVALID_INPUT", "Check the fields and their limits.")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException) -> JSONResponse:
        return failure(request, error.status_code, "HTTP_ERROR", "Requisition not available.")

    @app.exception_handler(Exception)
    async def unexpected(request: Request, error: Exception) -> JSONResponse:
        return failure(request, 500, "INTERNAL_ERROR", "Could not complete the operation.")
