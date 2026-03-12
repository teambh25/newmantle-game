import redis.asyncio as redis

from app.features.common.redis_keys import RedisQuizData, RedisQuizKeys


class AdminRepo:
    def __init__(self, rd: redis.Redis):
        self.rd = rd

    async def upsert_quiz(self, quiz: RedisQuizData):
        async with self.rd.pipeline(transaction=True) as pipe:
            pipe.set(quiz.keys.answers_key, quiz.answer, exat=quiz.expire_at)
            pipe.hset(quiz.keys.scores_key, mapping=quiz.scores_map)
            pipe.expireat(quiz.keys.scores_key, quiz.expire_at)
            pipe.hset(quiz.keys.ranking_key, mapping=quiz.ranking_map)
            pipe.expireat(quiz.keys.ranking_key, quiz.expire_at)
            await pipe.execute()

    async def fetch_all_answers(self):
        answer_keys = await self.rd.keys("*answers")
        answers = await self.rd.mget(answer_keys)
        return answer_keys, answers

    async def delete_quiz(self, keys: RedisQuizKeys):
        deleted_cnt = await self.rd.delete(
            keys.answers_key, keys.scores_key, keys.ranking_key
        )
        return deleted_cnt
