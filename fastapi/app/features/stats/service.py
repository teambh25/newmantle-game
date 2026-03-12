import datetime

from app.features.stats.repository import StatRepository


class StatService:
    def __init__(
        self,
        repo: StatRepository,
        today: datetime.date,
    ):
        self.repo = repo
        self.today = today

    async def record_guess(
        self, user_id: str, quiz_date: datetime.date, is_correct: bool
    ) -> None:
        """Record a guess. Sets status to SUCCESS on correct, FAIL on wrong."""
        await self.repo.record_guess(user_id, quiz_date, is_correct)

    async def record_hint(self, user_id: str, quiz_date: datetime.date) -> None:
        """Record a hint usage."""
        await self.repo.record_hint(user_id, quiz_date)

    async def record_giveup(self, user_id: str, quiz_date: datetime.date) -> None:
        """Record a give-up."""
        await self.repo.record_giveup(user_id, quiz_date)

    ######## 여기 아래는 나중에 체크!! ##########3
    # async def get_today_stat(
    #     self, user_id: str, quiz_date: datetime.date
    # ) -> dict | None:
    #     """Get today's stat from Redis."""
    #     keys = RedisStatKeys.from_user_and_date(user_id, quiz_date)
    #     data = await self.redis.hgetall(keys.key)
    #     if not data:
    #         return None
    #     return {
    #         "status": data.get(keys.F_STATUS, "FAIL"),
    #         "guess_count": int(data.get(keys.F_GUESSES, 0)),
    #         "hint_count": int(data.get(keys.F_HINTS, 0)),
    #     }

    # async def get_calendar(
    #     self,
    #     user_id: str,
    #     start_date: datetime.date,
    #     end_date: datetime.date,
    # ) -> list[dict]:
    #     """Fetch quiz results for calendar view. Merges today's Redis data with past DB data."""
    #     results = await self.repo.fetch_results_by_range(
    #         user_id, start_date, end_date
    #     )
    #     calendar = [
    #         {
    #             "date": r.quiz_date,
    #             "status": r.status.value,
    #             "guess_count": r.guess_count,
    #             "hint_count": r.hint_count,
    #         }
    #         for r in results
    #     ]

    #     # Merge today's data from Redis if in range
    #     if start_date <= self.today <= end_date:
    #         today_stat = await self.get_today_stat(user_id, self.today)
    #         if today_stat:
    #             calendar = [c for c in calendar if c["date"] != self.today]
    #             calendar.append({"date": self.today, **today_stat})
    #             calendar.sort(key=lambda c: c["date"])

    #     return calendar

    # async def get_streak(self, user_id: str) -> int:
    #     """Calculate current consecutive success days."""
    #     results = await self.repo.fetch_results_by_range(
    #         user_id,
    #         self.today - datetime.timedelta(days=365),
    #         self.today,
    #     )
    #     outage_dates = await self._get_outage_dates()

    #     result_map = {r.quiz_date: r.status.value for r in results}

    #     # Merge today's Redis data
    #     today_stat = await self.get_today_stat(user_id, self.today)
    #     if today_stat:
    #         result_map[self.today] = today_stat["status"]

    #     # If today is not SUCCESS, start counting from yesterday
    #     start = self.today
    #     if result_map.get(self.today) != "SUCCESS":
    #         start = self.today - datetime.timedelta(days=1)

    #     streak = 0
    #     current = start
    #     while True:
    #         if current in outage_dates:
    #             current -= datetime.timedelta(days=1)
    #             continue
    #         if result_map.get(current) == "SUCCESS":
    #             streak += 1
    #             current -= datetime.timedelta(days=1)
    #         else:
    #             break

    #     return streak

    # async def _get_outage_dates(self) -> set[datetime.date]:
    #     """Get outage dates with Redis caching."""
    #     cached = await self.redis.smembers(RedisStatKeys.OUTAGE_CACHE_KEY)
    #     if cached:
    #         return {datetime.date.fromisoformat(d) for d in cached}

    #     dates = await self.repo.fetch_outage_dates()
    #     if dates:
    #         await self.redis.sadd(
    #             RedisStatKeys.OUTAGE_CACHE_KEY, *[d.isoformat() for d in dates]
    #         )
    #         await self.redis.expire(
    #             RedisStatKeys.OUTAGE_CACHE_KEY, RedisStatKeys.OUTAGE_CACHE_TTL
    #         )
    #     return set(dates)

    # async def invalidate_outage_cache(self) -> None:
    #     """Clear outage dates cache (called after admin changes)."""
    #     await self.redis.delete(RedisStatKeys.OUTAGE_CACHE_KEY)
