import datetime

import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.common.redis_keys import RedisStatKeys
from app.features.common.redis_scripts import (
    RECORD_GIVEUP_SCRIPT,
    RECORD_GUESS_SCRIPT,
    RECORD_HINT_SCRIPT,
)
from app.features.stats.dto import QuizResultEntry, ResultMap
from app.models import UserQuizResult


class StatRepository:
    def __init__(self, session: AsyncSession, redis_client: redis.Redis):
        self.session = session
        self.redis = redis_client
        self._guess_script = self.redis.register_script(RECORD_GUESS_SCRIPT)
        self._hint_script = self.redis.register_script(RECORD_HINT_SCRIPT)
        self._giveup_script = self.redis.register_script(RECORD_GIVEUP_SCRIPT)

    # --- Redis: recording ---

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

    async def fetch_stat(
        self, user_id: str, quiz_date: datetime.date
    ) -> QuizResultEntry | None:
        """Get a single date's stat from Redis Hash. Returns None if no data."""
        keys = RedisStatKeys.from_user_and_date(user_id, quiz_date)
        data = await self.redis.hgetall(keys.key)
        if not data:
            return None
        return QuizResultEntry(
            status=data["status"],
            guess_count=int(data.get("guesses", 0)),
            hint_count=int(data.get("hints", 0)),
        )

    async def fetch_recent_stats(
        self, user_id: str, end_date: datetime.date
    ) -> dict[datetime.date, QuizResultEntry]:
        """Fetch stat keys for the last 7 days (TTL window) via pipeline."""
        dates = [end_date - datetime.timedelta(days=i) for i in range(7)]
        async with self.redis.pipeline(transaction=False) as pipe:
            for d in dates:
                keys = RedisStatKeys.from_user_and_date(user_id, d)
                pipe.hgetall(keys.key)
            responses = await pipe.execute()

        results: dict[datetime.date, QuizResultEntry] = {}
        for d, data in zip(dates, responses):
            if not data:
                continue
            results[d] = QuizResultEntry(
                status=data["status"],
                guess_count=int(data.get("guesses", 0)),
                hint_count=int(data.get("hints", 0)),
            )
        return results

    # --- DB: query ---

    async def fetch_all_results(
        self, user_id: str, end_date: datetime.date
    ) -> ResultMap:
        """Fetch all records from DB + Redis merged. Redis takes priority for same date."""
        stmt = (
            select(UserQuizResult)
            .where(UserQuizResult.user_id == user_id)
            .order_by(UserQuizResult.quiz_date)
        )
        db_result = await self.session.execute(stmt)
        result_map: ResultMap = {}
        for r in db_result.scalars().all():
            result_map[r.quiz_date] = QuizResultEntry(
                status=r.status.value,
                guess_count=r.guess_count,
                hint_count=r.hint_count,
            )

        # Redis recent stats (overwrites DB for same date)
        redis_stats = await self.fetch_recent_stats(user_id, end_date)
        result_map.update(redis_stats)

        return result_map

    # --- Batch: Redis → DB flush ---

    async def flush_stats(self, quiz_date: datetime.date) -> tuple[int, int]:
        """Scan Redis stats for a date and flush to DB in streaming chunks.

        Processes keys in CHUNK_SIZE batches during SCAN iteration
        to avoid loading all keys into memory at once.

        Returns (flushed_count, skipped_count).
        """
        pattern = f"user:*:quiz:{quiz_date}:stat"

        CHUNK_SIZE = 1000
        keys_chunk: list[str] = []

        total_flushed = 0
        total_skipped = 0

        async for key in self.redis.scan_iter(match=pattern, count=CHUNK_SIZE):
            keys_chunk.append(key)

            if len(keys_chunk) >= CHUNK_SIZE:
                flushed, skipped = await self._process_and_upsert_chunk(
                    quiz_date, keys_chunk
                )
                total_flushed += flushed
                total_skipped += skipped
                keys_chunk.clear()

        # Flush remaining keys
        if keys_chunk:
            flushed, skipped = await self._process_and_upsert_chunk(
                quiz_date, keys_chunk
            )
            total_flushed += flushed
            total_skipped += skipped

        return total_flushed, total_skipped

    async def _process_and_upsert_chunk(
        self, quiz_date: datetime.date, keys: list[str]
    ) -> tuple[int, int]:
        """Fetch hash data for keys via pipeline, parse into DB rows, and upsert."""
        async with self.redis.pipeline(transaction=False) as pipe:
            for key in keys:
                pipe.hgetall(key)
            responses = await pipe.execute()

        rows: list[dict] = []
        skipped = 0

        for key, data in zip(keys, responses):
            if not data:
                continue

            status = data.get("status")
            if status is None:
                skipped += 1
                continue

            user_id = key.split(":")[1]
            rows.append(
                {
                    "user_id": user_id,
                    "quiz_date": quiz_date,
                    "status": status,
                    "guess_count": int(data.get("guesses", 0)),
                    "hint_count": int(data.get("hints", 0)),
                }
            )

        if rows:
            await self._upsert_results(rows)

        return len(rows), skipped

    async def _upsert_results(self, results: list[dict]) -> None:
        """Batch upsert quiz results.

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
