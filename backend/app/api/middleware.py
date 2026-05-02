from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

ERROR_CODE_MAP = {
    400: "BAD_REQUEST",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
}


class AppError(Exception):
    """Application-level business error with structured code/message format."""

    def __init__(self, code: str, message: str, status_code: int = 400, detail: str | None = None) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "detail": self.detail}


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning("AppError: %s — %s", exc.code, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    error_code = ERROR_CODE_MAP.get(exc.status_code, "UNKNOWN")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": error_code,
            "code": error_code,
            "message": str(exc.detail),
            "detail": str(exc.detail),
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("未处理的异常")
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "code": "INTERNAL_ERROR",
            "message": "服务器内部错误",
            "detail": "服务器内部错误",
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
