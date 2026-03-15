import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

import app.exceptions as exc
import app.schemas as schemas
from app.cores.auth import authenticate_admin
from app.dependencies import get_admin_service
from app.features.admin.service import AdminService

admin_router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(authenticate_admin)],
)


@admin_router.put("/quizzes", status_code=status.HTTP_200_OK)
async def upsert_quiz(
    quiz: schemas.Quiz,
    admin_service: AdminService = Depends(get_admin_service),
):
    try:
        await admin_service.upsert_quiz(quiz)
    except exc.QuizValidationError as e:
        logger.error(str(e))
        raise HTTPException(status_code=422, detail=e.msg)
    logger.success(f"quiz created: {quiz.date}, {quiz.answer}")
    return {quiz.date: quiz.answer}


@admin_router.get("/quizzes/answers", status_code=status.HTTP_200_OK)
async def read_all_answers(
    admin_service: AdminService = Depends(get_admin_service),
):
    answers = await admin_service.read_all_answers()
    return answers


@admin_router.delete("/quizzes/{date}", status_code=status.HTTP_200_OK)
async def delete_answer(
    date: datetime.date,
    admin_service: AdminService = Depends(get_admin_service),
):
    try:
        await admin_service.delete_quiz(date)
    except exc.DateNotAllowed as e:
        logger.error(str(e))
        raise HTTPException(status_code=422, detail=e.msg)
    except exc.QuizNotFound as e:
        logger.error(str(e))
        raise HTTPException(status_code=404, detail=e.msg)
    except exc.QuizInconsistentError as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail=e.msg)
    logger.success(f"quiz deleted: {date}")


@admin_router.get(
    "/outage-dates",
    status_code=status.HTTP_200_OK,
    response_model=schemas.OutageDateListResp,
)
async def get_outage_dates(
    admin_service: AdminService = Depends(get_admin_service),
):
    dates = await admin_service.get_outage_dates()
    return schemas.OutageDateListResp(outage_dates=dates)


@admin_router.post(
    "/outage-dates",
    status_code=status.HTTP_201_CREATED,
)
async def create_outage_date(
    body: schemas.OutageDateRequest,
    admin_service: AdminService = Depends(get_admin_service),
):
    await admin_service.create_outage_date(body.date)
    logger.success(f"outage date created: {body.date}")
    return {"date": body.date}


@admin_router.delete(
    "/outage-dates/{date}",
    status_code=status.HTTP_200_OK,
)
async def delete_outage_date(
    date: datetime.date,
    admin_service: AdminService = Depends(get_admin_service),
):
    try:
        await admin_service.delete_outage_date(date)
    except exc.OutageDateNotFound as e:
        logger.error(str(e))
        raise HTTPException(status_code=404, detail=e.msg)
    logger.success(f"outage date deleted: {date}")
    return {"date": date}
