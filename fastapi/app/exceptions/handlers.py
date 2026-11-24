from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger

from .exceptions import AuthenticationFailed


async def global_exception_handler(request: Request, exc: Exception):
    logger.opt(exception=exc).error(
        "Unhandled exception | method={} path={} exception={}",
        request.method,
        request.url.path,
        type(exc).__name__,
    )
    return JSONResponse(status_code=500, content={"detail": "Server error"})


async def authentication_exception_handler(request: Request, exc: AuthenticationFailed):
    logger.info(
        "{} | method={} path={}",
        exc,
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=401,
        content={"detail": "Authentication failed"},
    )
