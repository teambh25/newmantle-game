import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OutageDate


class OutageDateRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def fetch_all(self) -> list[datetime.date]:
        stmt = select(OutageDate.date).order_by(OutageDate.date)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def insert(self, date: datetime.date) -> None:
        stmt = (
            insert(OutageDate)
            .values(date=date)
            .on_conflict_do_nothing(index_elements=["date"])
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def delete(self, date: datetime.date) -> bool:
        stmt = select(OutageDate).where(OutageDate.date == date)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if record:
            await self.session.delete(record)
            await self.session.commit()
            return True
        return False
