import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, status
from loguru import logger

import app.exceptions as exc
import app.schemas as schemas
from app.cores.config import configs
from app.dependencies import get_game_service_v2
from app.features.game.v2.service import GameServiceV2

game_router_v2 = APIRouter(prefix="/v2", tags=["Game-V2"])
game_logger = logger.bind(game=True)


@game_router_v2.get(
    "/quizzes/{date}/guess/{word}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.GuessResp,
)
async def guess(
    date: datetime.date,
    word: str,
    game_service: GameServiceV2 = Depends(get_game_service_v2),
):
    try:
        resp = await game_service.guess(date, word)
    except exc.WordNotFound as e:
        game_logger.info(f"v2 | guess | {e.msg}")
        raise HTTPException(status_code=404, detail="Invalid guess request")
    except exc.QuizNotFound as e:
        game_logger.info(f"v2 | guess | {e.msg}")
        raise HTTPException(status_code=500, detail="Can't find answer")
    return resp


@game_router_v2.get(
    "/quizzes/{date}/hint/{rank}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.HintResp,
)
async def hint(
    date: datetime.date,
    rank: int = Path(ge=0, le=configs.max_rank),
    game_service: GameServiceV2 = Depends(get_game_service_v2),
):
    try:
        resp = await game_service.hint(date, rank)
    except exc.RankNotFound as e:
        game_logger.info(f"v2 | hint | {e.msg}")
        raise HTTPException(status_code=404, detail="Invalid hint request")
    return resp


@game_router_v2.get(
    "/quizzes/{date}/give-up",
    status_code=status.HTTP_200_OK,
    response_model=schemas.GiveUpResp,
)
async def give_up(
    date: datetime.date,
    game_service: GameServiceV2 = Depends(get_game_service_v2),
):
    try:
        resp = await game_service.give_up(date)
    except exc.DateNotAllowed as e:
        game_logger.info(f"v2 | give up | {e.msg}")
        raise HTTPException(status_code=422, detail="Invalid give up request")
    except exc.QuizNotFound as e:
        game_logger.info(f"v2 | give up | {e.msg}")
        raise HTTPException(status_code=404, detail="Invalid give up request")
    return resp
