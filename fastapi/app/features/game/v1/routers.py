import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, status
from loguru import logger

import app.exceptions as exc
from app.cores.config import configs
from app.dependencies import get_game_service_v1
from app.features.game.v1.service import GameServiceV1

game_router_v1 = APIRouter(tags=["Game"])
game_logger = logger.bind(game=True)


@game_router_v1.get("/quizzes/{date}/guess/{word}", status_code=status.HTTP_200_OK)
async def guess(
    date: datetime.date,
    word: str,
    game_service: GameServiceV1 = Depends(get_game_service_v1),
):
    try:
        resp = await game_service.guess(date, word)
    except exc.WordNotFound as e:
        game_logger.info(e.msg)
        raise HTTPException(status_code=400, detail="Invalid guess request")
    return resp


@game_router_v1.get("/quizzes/{date}/hint/{rank}", status_code=status.HTTP_200_OK)
async def hint(
    date: datetime.date,
    rank: int = Path(ge=0, le=configs.max_rank),
    game_service: GameServiceV1 = Depends(get_game_service_v1),
):
    try:
        resp = await game_service.hint(date, rank)
    except exc.RankNotFound as e:
        game_logger.info(e.msg)
        raise HTTPException(status_code=400, detail="Invalid hint request")
    return resp


@game_router_v1.get("/quizzes/{date}/recent-answer", status_code=status.HTTP_200_OK)
async def recent_answer(
    date: datetime.date,
    game_service: GameServiceV1 = Depends(get_game_service_v1),
):
    try:
        resp = await game_service.read_recent_answer(date)
    except exc.DateNotAllowed as e:
        game_logger.info(e.msg)
        raise HTTPException(status_code=400, detail="Invalid recent-answer request")
    except exc.QuizNotFound as e:
        game_logger.info(e.msg)
        raise HTTPException(status_code=400, detail="Invalid recent-answer request")
    return resp
