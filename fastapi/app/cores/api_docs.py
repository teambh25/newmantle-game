from fastapi import APIRouter, Depends, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from app.cores.auth import authenticate_admin

docs_router = APIRouter(
    tags=["docs"],
    include_in_schema=False,
    dependencies=[Depends(authenticate_admin)],  # authorization for API docs
)


@docs_router.get("/docs")
async def get_documentation(request: Request):
    return get_swagger_ui_html(openapi_url=request.app.openapi_url, title="Docs")


@docs_router.get("/openapi")
async def get_open_api_endpoint(request: Request):
    return get_openapi(
        title="newmantle API", version="2.0.0", routes=request.app.routes
    )
