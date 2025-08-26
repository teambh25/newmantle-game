import datetime

from fastapi import Depends, APIRouter, HTTPException, status
from loguru import logger

import app.features.admin.schemas as schemas
from app.cores.auth import authenticate_admin
import app.exceptions as exceptions
from app.dependencies import get_admin_service
from app.features.admin.service import AdminService

admin_router = APIRouter(prefix="/admin", tags=["Admin"])

@admin_router.put("/quizzes", status_code=status.HTTP_200_OK)
async def upsert_quiz(
    quiz: schemas.Quiz, 
    admin_service: AdminService = Depends(get_admin_service),
    _: bool = Depends(authenticate_admin)
):
    try:
        await admin_service.upsert_quiz(quiz)
    except exceptions.InvalidParameter as e:
        logger.error(str(e))
        raise HTTPException(status_code=404, detail=e.msg)
    return {quiz.date:quiz.answer}


@admin_router.get("/quizzes/answers", status_code=status.HTTP_200_OK)
async def read_all_answers(
    admin_service: AdminService = Depends(get_admin_service),
    _: bool = Depends(authenticate_admin)
):
    answers = await admin_service.read_all_answers()
    return answers


@admin_router.delete('/quizzes/{date}', status_code=status.HTTP_200_OK)
async def delete_answer(
    date: datetime.date,
    admin_service: AdminService = Depends(get_admin_service),
    _: bool = Depends(authenticate_admin)
):  
    try:
        deleted_cnt = await admin_service.delete_quiz(date)
    except exceptions.InvalidParameter as e:
        logger.error(str(e))
        raise HTTPException(status_code=404, detail=e.msg)
    return {"details":f"{deleted_cnt} keys are deleted"}