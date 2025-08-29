import redis.asyncio as redis


class GameRepo:
    def __init__(self, rd: redis.Redis):
        self.rd = rd
    
    async def get_score_rank_by_word(self, scores_key: str, word: str) -> str:
        return await self.rd.hget(scores_key, word)
    
    async def get_word_score_by_rank(self, ranking_key: str, rank: int) -> str:
        return await self.rd.hget(ranking_key, rank)