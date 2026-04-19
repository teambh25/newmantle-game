import redis.asyncio as redis

from app.features.common.redis_keys import RedisQuizData, RedisQuizKeys


class AdminRepo:
    def __init__(self, rd: redis.Redis):
        self.rd = rd

    async def upsert_quiz(self, quiz: RedisQuizData):
        # Write to temp keys then RENAME so stale fields from a previous
        # upsert (e.g. shrunk word pool) are dropped atomically.
        tmp_scores_key = quiz.keys.scores_key + ":tmp"
        tmp_ranking_key = quiz.keys.ranking_key + ":tmp"
        async with self.rd.pipeline(transaction=True) as pipe:
            pipe.unlink(tmp_scores_key, tmp_ranking_key)
            pipe.hset(tmp_scores_key, mapping=quiz.scores_map)
            pipe.hset(tmp_ranking_key, mapping=quiz.ranking_map)
            pipe.expireat(tmp_scores_key, quiz.expire_at)
            pipe.expireat(tmp_ranking_key, quiz.expire_at)
            pipe.rename(tmp_scores_key, quiz.keys.scores_key)
            pipe.rename(tmp_ranking_key, quiz.keys.ranking_key)
            pipe.set(quiz.keys.answers_key, quiz.answer, exat=quiz.expire_at)
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
            pipe.unlink(keys.answers_key, keys.scores_key, keys.ranking_key)
            pipe.srem("quiz:index", keys.answers_key)
            results = await pipe.execute()
        return results[0]
