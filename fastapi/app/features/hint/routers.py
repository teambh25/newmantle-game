# from datetime import date

# from fastapi import Depends, APIRouter, HTTPException, Path
# from fastapi.responses import JSONResponse

# from app.cores.config import configs
# from dependencies import get_daily_quiz
# from app.services import QuizService
# from app.common.utils import extract_initial_consonant

# router = APIRouter(prefix='/hint', tags=['Hint'])

# @router.get('/{req_date}/{req_rank}')
# def hint(req_date: date, req_rank: int = Path(ge=0, le=configs.max_rank), daily_quiz: dict = Depends(get_daily_quiz)):
#     if (quiz := daily_quiz.get(req_date)) is None:
#         raise HTTPException(status_code=404, detail='No resource found that match the given date')
#     if req_rank == 0: # 정답 단어 힌트
#         initial_consonant = extract_initial_consonant(quiz.answer)
#         resp = {'hint': initial_consonant, 'score': None}
#     else:
#         hint_word, hint_score = QuizService.get_nth_rank_word(quiz, req_rank)
#         resp = {'hint': hint_word, 'score': hint_score}
#     return JSONResponse(content=resp)