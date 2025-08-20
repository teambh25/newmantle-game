from fastapi import Depends, APIRouter, HTTPException, status
import redis.asyncio as redis

import app.features.admin.schemas as schemas
from app.cores.redis import get_redis_client
from app.cores.auth import authenticate_admin

admin_router = APIRouter(prefix='/admin', tags=['Admin'])

@admin_router.post('/quizzes', status_code=status.HTTP_201_CREATED)
async def create_quiz(
    params: schemas.Quiz, 
    redis_client: redis.Redis = Depends(get_redis_client),
    _: bool = Depends(authenticate_admin)
):
    
    return params.scores