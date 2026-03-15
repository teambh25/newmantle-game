import datetime

import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.common.redis_keys import RedisStatKeys
from app.features.stats.models import OutageDate, UserQuizResult
from app.features.common.redis_scripts import (
    RECORD_GIVEUP_SCRIPT,
    RECORD_GUESS_SCRIPT,
    RECORD_HINT_SCRIPT,
)


class StatRepository:
    def __init__(self, session: AsyncSession, redis_client: redis.Redis):
        self.session = session
        self.redis = redis_client
        self._guess_script = self.redis.register_script(RECORD_GUESS_SCRIPT)
        self._hint_script = self.redis.register_script(RECORD_HINT_SCRIPT)
        self._giveup_script = self.redis.register_script(RECORD_GIVEUP_SCRIPT)

    # --- Redis: game-time stat recording ---

    async def record_guess(
        self, user_id: str, quiz_date: datetime.date, is_correct: bool
    ) -> None:
        keys = RedisStatKeys.from_user_and_date(user_id, quiz_date)
        result = "SUCCESS" if is_correct else "WRONG"
        await self._guess_script(keys=[keys.key], args=[result, keys.ttl])

    async def record_hint(self, user_id: str, quiz_date: datetime.date) -> None:
        keys = RedisStatKeys.from_user_and_date(user_id, quiz_date)
        await self._hint_script(keys=[keys.key], args=[keys.ttl])

    async def record_giveup(self, user_id: str, quiz_date: datetime.date) -> None:
        keys = RedisStatKeys.from_user_and_date(user_id, quiz_date)
        await self._giveup_script(keys=[keys.key], args=[keys.ttl])

    # --- Redis: query ---

    async def fetch_redis_stat(
        self, user_id: str, quiz_date: datetime.date
    ) -> dict | None:
        """Get a single date's stat from Redis Hash. Returns None if no data."""
        keys = RedisStatKeys.from_user_and_date(user_id, quiz_date)
        data = await self.redis.hgetall(keys.key)
        if not data:
            return None
        return {
            "date": quiz_date,
            "status": data.get("status", "FAIL"),
            "guess_count": int(data.get("guesses", 0)),
            "hint_count": int(data.get("hints", 0)),
        }

    async def fetch_recent_redis_stats(
        self, user_id: str, end_date: datetime.date
    ) -> list[dict]:
        """Fetch stat keys for the last 7 days (TTL window) via pipeline."""
        dates = [end_date - datetime.timedelta(days=i) for i in range(7)]
        async with self.redis.pipeline(transaction=False) as pipe:
            for d in dates:
                keys = RedisStatKeys.from_user_and_date(user_id, d)
                pipe.hgetall(keys.key)
            responses = await pipe.execute()

        results = []
        for d, data in zip(dates, responses):
            if not data:
                continue
            results.append({
                "date": d,
                "status": data.get("status", "FAIL"),
                "guess_count": int(data.get("guesses", 0)),
                "hint_count": int(data.get("hints", 0)),
            })
        return results

    # --- DB: batch & query ---

    async def upsert_results(self, results: list[dict]) -> None:
        """Batch upsert quiz results from Redis flush.

        Each dict: {user_id, quiz_date, status, guess_count, hint_count}
        """
        if not results:
            return
        stmt = insert(UserQuizResult).values(results)
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "quiz_date"],
            set_={
                "status": stmt.excluded.status,
                "guess_count": stmt.excluded.guess_count,
                "hint_count": stmt.excluded.hint_count,
            },
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def fetch_all_results(
        self, user_id: str, end_date: datetime.date
    ) -> dict[datetime.date, dict]:
        """Fetch all records from DB + Redis merged. Redis takes priority for same date.

        Returns: {date: {"status": str, "guess_count": int, "hint_count": int}}
        """
        # DB full scan
        stmt = (
            select(UserQuizResult)
            .where(UserQuizResult.user_id == user_id)
            .order_by(UserQuizResult.quiz_date)
        )
        db_result = await self.session.execute(stmt)
        result_map: dict[datetime.date, dict] = {}
        for r in db_result.scalars().all():
            result_map[r.quiz_date] = {
                "status": r.status.value,
                "guess_count": r.guess_count,
                "hint_count": r.hint_count,
            }

        # Redis recent stats (overwrites DB for same date)
        redis_stats = await self.fetch_recent_redis_stats(user_id, end_date)
        for s in redis_stats:
            result_map[s["date"]] = {
                "status": s["status"],
                "guess_count": s["guess_count"],
                "hint_count": s["hint_count"],
            }

        return result_map

    async def fetch_outage_dates(self) -> list[datetime.date]:
        """Fetch all records, ordered by date."""
        stmt = select(OutageDate.date).order_by(OutageDate.date)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def insert_outage_date(self, date: datetime.date) -> None:
        stmt = (
            insert(OutageDate)
            .values(date=date)
            .on_conflict_do_nothing(index_elements=["date"])
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def delete_outage_date(self, date: datetime.date) -> bool:
        stmt = select(OutageDate).where(OutageDate.date == date)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if record:
            await self.session.delete(record)
            await self.session.commit()
            return True
        return False
