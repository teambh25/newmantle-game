import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.stats.models import OutageDate, UserQuizResult


class StatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

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

    async def fetch_results_by_range(
        self,
        user_id: str,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> list[UserQuizResult]:
        """Fetch records within a date range, ordered by quiz_date."""
        stmt = (
            select(UserQuizResult)
            .where(
                UserQuizResult.user_id == user_id,
                UserQuizResult.quiz_date >= start_date,
                UserQuizResult.quiz_date <= end_date,
            )
            .order_by(UserQuizResult.quiz_date)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

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
