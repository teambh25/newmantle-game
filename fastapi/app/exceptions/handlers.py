from fastapi import Request, HTTPException
from loguru import logger

from .exceptions import AuthenticationFailed

async def unexpected_exception_handler(request: Request, exc: Exception):
    logger.critical(f"UnexpectedException: '{exc.__class__.__name__}: {str(exc)}'")
    raise HTTPException(status_code=500, detail="Server error")


async def authentication_exception_handler(request: Request, exc: AuthenticationFailed):
    logger.error(str(exc))
    raise HTTPException(status_code=401, detail="Authentication failed")


# async def redis_connection_exception_handler(request: Request, exc: redis_exceptions.ConnectionError):
#     logger.critical(f"Redis connection error : {str(exc)}")
#     return HTTPException(status_code=503, detail="The service is temporarily unavailable. Please try again later") # Service Unavailable


# async def redis_timeout_exception_handler(request: Request, exc: redis_exceptions.TimeoutError):
#     logger.critical(f"Redis timeout : {str(exc)}")
#     return HTTPException(status_code=504, detail="The service is temporarily unavailable. Please try again later") # Gateway Timeout