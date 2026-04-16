from fastapi import HTTPException, Request
from loguru import logger

from .exceptions import AuthenticationFailed


async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    raise HTTPException(status_code=500, detail="Server error")


async def authentication_exception_handler(request: Request, exc: AuthenticationFailed):
    logger.info(str(exc))
    raise HTTPException(status_code=401, detail="Authentication failed")
