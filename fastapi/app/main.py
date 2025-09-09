from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.cores.event import lifespan
from app.cores.config import configs
from app.features.admin.routers import admin_router
import app.exceptions as exceptions
from app.features.game.routers import game_router

from app.cores.auth import authenticate_admin
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
)

@app.get("/docs", include_in_schema=False)
async def get_documentation(_: bool = Depends(authenticate_admin)):
    return get_swagger_ui_html(openapi_url=app.openapi_url, title="Docs")

# 4. OpenAPI 스키마 자체도 보호
@app.get(app.openapi_url, include_in_schema=False)
async def get_open_api_endpoint(_: bool = Depends(authenticate_admin)):
    return get_openapi(title="newmantle API", version="2.0.0", routes=app.routes)

app.include_router(admin_router)
app.include_router(game_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=configs.allowed_origins,
    allow_origin_regex=configs.allowed_origin_regex,
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