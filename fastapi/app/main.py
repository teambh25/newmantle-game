from fastapi import FastAPI, Request, HTTPException
from loguru import logger

from app.cores.event import lifespan
from app.features.admin.routers import admin_router
from app.common.exceptions import AuthenticationFailed

app = FastAPI(lifespan=lifespan)

app.include_router(admin_router)
# app.include_router(guess.router)
# app.include_router(hint.router)

# log 초기화도 lifespan 쪽으로 옮기기?????????????????
logger.remove()  # Remove default console handler
logger.add(
    './logs/{time:YYYY-MM-DD!UTC}_UTC.log',
    rotation='15:00',  # Rotate every KST(UTC+9) midnight
    retention='30 days',  # Keep 30 days of logs
    encoding='utf-8',
    format='{time:YYYY-MM-DD HH:mm:ss!UTC} | {level} | {message}'
)

@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception):
    logger.critical(f'UnexpectedException: {str(exc)}')
    raise HTTPException(status_code=500, detail='An unexpected error occurred')


@app.exception_handler(AuthenticationFailed)
async def authentication_exception_handler(request: Request, exc: AuthenticationFailed):
    logger.error(str(exc))
    raise HTTPException(status_code=401, detail='Authentication failed due to invalid credentials')