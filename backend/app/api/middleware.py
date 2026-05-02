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


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    error_code = ERROR_CODE_MAP.get(exc.status_code, "UNKNOWN")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error_code, "detail": exc.detail},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("未处理的异常")
    return JSONResponse(
        status_code=500,
        content={"error": "INTERNAL_ERROR", "detail": "服务器内部错误"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
