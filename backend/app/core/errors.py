import logging
from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """
    Standard application exception per backend-plan.md and api-spec.md.
    All business, validation, authorization, and provider errors should be raised as AppError.
    """

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


def build_error_response(
    code: str, message: str, status_code: int, details: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """
    Constructs the canonical JSON error response body required by api-spec.md:
    { "error": { "code": "...", "message": "...", "details": {} } }
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    """
    Registers application-wide exception handlers to ensure consistent error structure
    and prevent raw stack traces from leaking to clients.
    """

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "AppError raised: code=%s, status=%d, message=%s, path=%s",
            exc.code,
            exc.status_code,
            exc.message,
            request.url.path,
        )
        return build_error_response(
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning("Validation error on %s: %s", request.url.path, exc.errors())
        # Format Pydantic errors into a clean details dict
        formatted_errors = []
        for err in exc.errors():
            loc = " -> ".join(str(item) for item in err.get("loc", []))
            formatted_errors.append(
                {
                    "location": loc,
                    "message": err.get("msg"),
                    "type": err.get("type"),
                }
            )

        return build_error_response(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"errors": formatted_errors},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        status_code_map = {
            401: "UNAUTHENTICATED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            422: "VALIDATION_ERROR",
            500: "INTERNAL_SERVER_ERROR",
            502: "BAD_GATEWAY",
            503: "SERVICE_UNAVAILABLE",
        }
        code = status_code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
        message = (
            exc.detail if isinstance(exc.detail, str) else "An HTTP error occurred"
        )
        details = exc.detail if isinstance(exc.detail, dict) else {}

        return build_error_response(
            code=code,
            message=message,
            status_code=exc.status_code,
            details=details,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            "Unhandled server error on %s: %s",
            request.url.path,
            str(exc),
            exc_info=True,
        )
        return build_error_response(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={},
        )
