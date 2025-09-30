from fastapi import HTTPException, Request
from loguru import logger

from .exceptions import AuthenticationFailed


async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("")
    raise HTTPException(status_code=500, detail="Server error")


async def authentication_exception_handler(request: Request, exc: AuthenticationFailed):
    logger.error(str(exc))
    raise HTTPException(status_code=401, detail="Authentication failed")
