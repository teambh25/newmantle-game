from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine


def create_db_engine(db_url: str, pool_size: int, max_overflow: int) -> AsyncEngine:
    return create_async_engine(
        db_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,
        pool_recycle=300,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)
