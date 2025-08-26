# from datetime import date
# from typing import Annotated

# from fastapi import Depends, APIRouter, HTTPException, status
# from fastapi.responses import JSONResponse
# from redis.asyncio import Redis
# from sqlalchemy.orm import Session

# from app.cores.cache import get_redis
# from app.database.session import get_db
# from app.services import QuizService
# from app.exceptions import Error, NoDateInDailyQuiz, NoWordInDB

# router = APIRouter(prefix="/guess", tags=["Guess"])

# # Todo - 로깅
# @router.get("/{req_date}/{req_word}", status_code=status.HTTP_200_OK)
# async def guess(req_date: date, req_word: str, rd: Annotated[Redis, Depends(get_redis)], db: Annotated[Session, Depends(get_db)]):
#     try:
#         quiz = QuizService.get_quiz(req_date)
#         if QuizService.is_correct(quiz, req_word):
#             resp = {"correct": True, "score": None, "rank": None}
#         else:
#             score, rank = QuizService.get_score_and_rank(quiz, req_word, db)
#             resp = {"correct": False, "score": score, "rank": rank}
#     except NoDateInDailyQuiz:
#         raise HTTPException(status_code=404, detail="No resource found that match the given date")
#     except NoWordInDB:
#         raise HTTPException(status_code=404, detail="No resource found that match the given word")
#     except Error: # error does not handle
#         raise HTTPException(status_code=500, detail="Server error")
#     except Exception: # unexpected error
#         raise HTTPException(status_code=500, detail="Server unexpected error") 
#     return JSONResponse(content=resp)
