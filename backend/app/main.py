import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.specs import router as specs_router
from app.core.config import APP_NAME, APP_VERSION, FRONTEND_ORIGINS
from app.db.database import Database
from app.schemas.errors import ErrorBody, ErrorDetail, ErrorResponse
from app.services.openapi_parser import OpenAPIParseError

logger = logging.getLogger(__name__)


def _error_content(
    code: str,
    message: str,
    details: list[ErrorDetail] | None = None,
) -> dict[str, object]:
    error = ErrorBody(code=code, message=message, details=details or [])
    return ErrorResponse(error=error).model_dump(mode="json")


def create_app(database: Database | None = None) -> FastAPI:
    database = database or Database()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        database.create_schema()
        application.state.database = database
        try:
            yield
        finally:
            database.dispose()

    application = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=FRONTEND_ORIGINS,
        allow_methods=["GET", "POST"],
        allow_headers=["content-type"],
    )
    application.include_router(health_router)
    application.include_router(specs_router, prefix="/api/v1")

    @application.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exception: StarletteHTTPException
    ) -> JSONResponse:
        error_codes = {
            400: ("BAD_REQUEST", "The request could not be processed."),
            404: ("NOT_FOUND", "The requested resource was not found."),
            405: ("METHOD_NOT_ALLOWED", "The HTTP method is not allowed."),
            413: ("REQUEST_TOO_LARGE", "The request exceeds the allowed size."),
            422: ("VALIDATION_ERROR", "The request data is invalid."),
        }
        code, message = error_codes.get(
            exception.status_code,
            ("HTTP_ERROR", "The request could not be completed."),
        )
        return JSONResponse(
            status_code=exception.status_code,
            content=_error_content(code, message),
            headers=exception.headers,
        )

    @application.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request, exception: RequestValidationError
    ) -> JSONResponse:
        details = [
            ErrorDetail(
                field=".".join(str(part) for part in error["loc"]),
                code=str(error["type"]),
            )
            for error in exception.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_error_content(
                "VALIDATION_ERROR", "The request data is invalid.", details
            ),
        )

    @application.exception_handler(OpenAPIParseError)
    async def handle_openapi_parse_error(
        request: Request, exception: OpenAPIParseError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_error_content("INVALID_OPENAPI_SPEC", str(exception)),
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_exception(
        request: Request, exception: Exception
    ) -> JSONResponse:
        route = request.scope.get("route")
        route_path = getattr(route, "path", "<unmatched>")
        logger.error(
            "Unhandled application error on %s %s (%s)",
            request.method,
            route_path,
            type(exception).__name__,
        )
        return JSONResponse(
            status_code=500,
            content=_error_content(
                "INTERNAL_SERVER_ERROR", "An unexpected error occurred."
            ),
        )

    return application


app = create_app()
