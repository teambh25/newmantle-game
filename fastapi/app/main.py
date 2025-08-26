from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger

from app.cores.event import lifespan
from app.features.admin.routers import admin_router
import app.exceptions as exceptions

app = FastAPI(lifespan=lifespan)

app.include_router(admin_router)
# app.include_router(guess.router)
# app.include_router(hint.router)

logger.remove()  # Remove default console handler
logger.add(
    "./logs/{time:YYYY-MM-DD!UTC}_UTC.log",
    rotation="15:00",  # Rotate every KST(UTC+9) midnight
    retention="30 days",  # Keep 30 days of logs
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss!UTC} | {level} | {message}"
)

EXCEPTION_HANDLERS = {
    Exception: exceptions.unexpected_exception_handler,
    exceptions.AuthenticationFailed: exceptions.authentication_exception_handler,
}

for exc, handler in EXCEPTION_HANDLERS.items():
    app.add_exception_handler(exc, handler)