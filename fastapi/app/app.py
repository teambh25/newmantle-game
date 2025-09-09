from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.cores.event import lifespan
from app.cores.config import configs
from app.cores.api_docs import docs_router
from app.features.admin.routers import admin_router
from app.features.game.routers import game_router
import app.exceptions as exceptions


def create_app() -> FastAPI:
    app = FastAPI(
        lifespan=lifespan,  # setup log and redis pool
        docs_url=None,      # disable default docs
        redoc_url=None, 
        openapi_url="/openapi.json",
    )
    
    # add routers
    app.include_router(docs_router)
    app.include_router(admin_router)
    app.include_router(game_router)

    # add CORS midleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=configs.allowed_origins,
        allow_origin_regex=configs.allowed_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # add exception handlers
    EXCEPTION_HANDLERS = {
        Exception: exceptions.global_exception_handler,
        exceptions.AuthenticationFailed: exceptions.authentication_exception_handler,
    }
    for exc, handler in EXCEPTION_HANDLERS.items():
        app.add_exception_handler(exc, handler)
    
    return app