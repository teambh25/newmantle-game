import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from loguru import logger

from app.cores.config import configs

game_router_v1 = APIRouter(tags=["Game"])


_GONE = HTTPException(status_code=status.HTTP_410_GONE, detail="This API version is no longer supported. Please use v2.")


@game_router_v1.get("/quizzes/{date}/guess/{word}", deprecated=True)
async def guess(request: Request, date: datetime.date, word: str):
    logger.warning(f"v1 deprecated endpoint called | path={request.url.path} | client={request.client.host}")
    raise _GONE


@game_router_v1.get("/quizzes/{date}/hint/{rank}", deprecated=True)
async def hint(request: Request, date: datetime.date, rank: int = Path(ge=0, le=configs.max_rank)):
    logger.warning(f"v1 deprecated endpoint called | path={request.url.path} | client={request.client.host}")
    raise _GONE


@game_router_v1.get("/quizzes/{date}/recent-answer", deprecated=True)
async def recent_answer(request: Request, date: datetime.date):
    logger.warning(f"v1 deprecated endpoint called | path={request.url.path} | client={request.client.host}")
    raise _GONE
