from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def get_db_session_factory(req: Request) -> async_sessionmaker:
    return req.app.state.db_session_factory


async def get_db_session(
    factory: async_sessionmaker = Depends(get_db_session_factory),
) -> AsyncGenerator[AsyncSession, None]:
    async with factory() as session:
        yield session
