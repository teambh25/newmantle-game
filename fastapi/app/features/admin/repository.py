import redis.asyncio as redis

import app.features.admin.schemas as schemas 
from app.cores.redis import RedisKeys

class AdminRepo:
    def __init__(self, rd: redis.Redis):
        self.rd = rd

    async def upsert_quiz(self, quiz: schemas.RedisQuizData):
        async with self.rd.pipeline(transaction=True) as pipe:
            pipe.set(quiz.keys.answers, quiz.answer_word, exat=quiz.expire_at)
            pipe.hset(quiz.keys.scores, mapping=quiz.scores_map)
            pipe.expireat(quiz.keys.scores, quiz.expire_at)
            pipe.hset(quiz.keys.ranking, mapping=quiz.ranking_map)
            pipe.expireat(quiz.keys.ranking, quiz.expire_at)
            await pipe.execute()

    async def fetch_all_answers(self):
        answer_keys = await self.rd.keys("*answers")
        answer_words = await self.rd.mget(answer_keys)
        return answer_keys, answer_words
    
    async def delete_quiz(self, keys: RedisKeys):
        deleted_cnt = await self.rd.delete(keys.answers, keys.scores, keys.ranking)
        return deleted_cnt