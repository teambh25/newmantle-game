import datetime

from fastapi import Depends, APIRouter, HTTPException, status, Path
from loguru import logger

from app.dependencies import get_game_service
from app.cores.config import configs
import app.exceptions as exceptions
from app.features.game.service import GameService

game_router = APIRouter(tags=["Game"])
game_logger = logger.bind(game=True)


@game_router.get("/quizzes/{date}/guess/{word}", status_code=status.HTTP_200_OK)
async def guess(
    date: datetime.date,
    word: str,
    game_service: GameService = Depends(get_game_service),
):
    try:
        resp = await game_service.guess(date, word)
    except exceptions.InvalidParameter as e:
        game_logger.info(e.msg)
        raise HTTPException(status_code=400, detail="Invalid guess request")
    return resp


@game_router.get("/quizzes/{date}/hint/{rank}", status_code=status.HTTP_200_OK)
async def hint(
    date: datetime.date,
    rank: int = Path(ge=0, le=configs.max_rank),
    game_service: GameService = Depends(get_game_service),
):
    try:
        resp = await game_service.hint(date, rank)
    except exceptions.InvalidParameter as e:
        game_logger.info(e.msg)
        raise HTTPException(status_code=400, detail="Invalid hint request")
    return resp