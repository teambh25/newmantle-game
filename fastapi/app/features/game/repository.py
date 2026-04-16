import redis.asyncio as redis


class GameRepo:
    def __init__(self, rd: redis.Redis):
        self.rd = rd

    async def fetch_key_exists_and_score_rank(
        self, scores_key: str, word: str
    ) -> tuple[bool, str | None]:
        async with self.rd.pipeline(transaction=False) as pipe:
            await pipe.exists(scores_key)
            await pipe.hget(scores_key, word)
            exists, score_rank = await pipe.execute()
        return bool(exists), score_rank

    async def fetch_word_score(self, ranking_key: str, rank: int) -> str | None:
        return await self.rd.hget(ranking_key, rank)

    async def fetch_answer_by_date(self, answer_key: str) -> str:
        return await self.rd.get(answer_key)
