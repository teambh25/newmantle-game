from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.cores.event import lifespan
from app.cores.config import settings
from app.features.admin.routers import admin_router
import app.exceptions as exceptions
from app.features.game.routers import game_router

from loguru import logger

app = FastAPI(lifespan=lifespan)
app.include_router(admin_router)
app.include_router(game_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=settings.allowed_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EXCEPTION_HANDLERS = {
    Exception: exceptions.global_exception_handler,
    exceptions.AuthenticationFailed: exceptions.authentication_exception_handler,
}

for exc, handler in EXCEPTION_HANDLERS.items():
    app.add_exception_handler(exc, handler)