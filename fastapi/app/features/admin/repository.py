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
            pipe.sadd("quiz:index", quiz.keys.answers_key)
            await pipe.execute()

    async def fetch_all_answers(self):
        answer_keys = list(await self.rd.smembers("quiz:index"))
        if not answer_keys:
            return [], []
        answers = await self.rd.mget(answer_keys)

        # Lazy cleanup: remove stale keys where TTL has expired
        live_keys, live_answers = [], []
        stale_keys = []
        for key, ans in zip(answer_keys, answers):
            if ans is not None:
                live_keys.append(key)
                live_answers.append(ans)
            else:
                stale_keys.append(key)
        if stale_keys:
            await self.rd.srem("quiz:index", *stale_keys)

        return live_keys, live_answers

    async def delete_quiz(self, keys: RedisQuizKeys):
        async with self.rd.pipeline(transaction=True) as pipe:
            pipe.delete(keys.answers_key, keys.scores_key, keys.ranking_key)
            pipe.srem("quiz:index", keys.answers_key)
            results = await pipe.execute()
        return results[0]
