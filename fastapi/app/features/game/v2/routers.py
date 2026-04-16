import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, status
from loguru import logger

import app.exceptions as exc
import app.schemas as schemas
from app.cores.auth import UserIdentity, get_current_subject
from app.cores.config import configs
from app.dependencies import get_game_service_v2, get_stat_service
from app.features.game.v2.service import GameServiceV2
from app.features.stats.service import StatService

game_router_v2 = APIRouter(prefix="/v2", tags=["Game-V2"])
event_logger = logger.bind(event=True)


@game_router_v2.get(
    "/quizzes/{date}/guess/{word}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.GuessResp,
)
async def guess(
    date: datetime.date,
    word: str,
    game_service: GameServiceV2 = Depends(get_game_service_v2),
    stat_service: StatService = Depends(get_stat_service),
    identity: UserIdentity = Depends(get_current_subject),
):
    try:
        correct, score, rank, answer = await game_service.guess(date, word)
    except exc.DateNotAllowed:
        event_logger.info(
            "guess_invalid_date",
            user_id=identity.id,
            user_type=identity.user_type,
            date=str(date),
        )
        raise HTTPException(status_code=422, detail="Invalid guess request")
    except exc.WordNotFound:
        event_logger.info(
            "guess_invalid_word",
            user_id=identity.id,
            user_type=identity.user_type,
            date=str(date),
            word=word,
        )
        raise HTTPException(status_code=404, detail="Invalid guess request")

    event_logger.info(
        "guess",
        user_id=identity.id,
        user_type=identity.user_type,
        date=str(date),
        correct=correct,
        word=word,
        rank=rank,
        score=score,
    )
    await stat_service.record_guess(identity, date, correct)
    return schemas.GuessResp(correct=correct, score=score, rank=rank, answer=answer)


@game_router_v2.get(
    "/quizzes/{date}/hint/{rank}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.HintResp,
)
async def hint(
    date: datetime.date,
    rank: int = Path(ge=0, le=configs.max_rank),
    game_service: GameServiceV2 = Depends(get_game_service_v2),
    stat_service: StatService = Depends(get_stat_service),
    identity: UserIdentity = Depends(get_current_subject),
):
    try:
        hint_word, score = await game_service.hint(date, rank)
    except exc.DateNotAllowed:
        event_logger.info(
            "hint_invalid_date",
            user_id=identity.id,
            user_type=identity.user_type,
            date=str(date),
        )
        raise HTTPException(status_code=422, detail="Invalid hint request")

    event_logger.info(
        "hint",
        user_id=identity.id,
        user_type=identity.user_type,
        date=str(date),
        rank=rank,
        hint=hint_word,
        score=score,
    )
    await stat_service.record_hint(identity, date)
    return schemas.HintResp(hint=hint_word, score=score)


@game_router_v2.get(
    "/quizzes/{date}/give-up",
    status_code=status.HTTP_200_OK,
    response_model=schemas.GiveUpResp,
)
async def give_up(
    date: datetime.date,
    game_service: GameServiceV2 = Depends(get_game_service_v2),
    stat_service: StatService = Depends(get_stat_service),
    identity: UserIdentity = Depends(get_current_subject),
):
    try:
        answer = await game_service.give_up(date)
    except exc.DateNotAllowed:
        event_logger.info(
            "give_up_invalid_date",
            user_id=identity.id,
            user_type=identity.user_type,
            date=str(date),
        )
        raise HTTPException(status_code=422, detail="Invalid give up request")

    event_logger.info(
        "give_up",
        user_id=identity.id,
        user_type=identity.user_type,
        date=str(date),
        answer=answer.word,
    )
    await stat_service.record_giveup(identity, date)
    return schemas.GiveUpResp(**answer.model_dump())
