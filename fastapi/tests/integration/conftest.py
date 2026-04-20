import pytest_asyncio
import redis.asyncio as redis

from app.cores.config import configs


@pytest_asyncio.fixture
async def redis_client():
    client = redis.from_url(configs.test_redis_url, decode_responses=True)
    yield client
    await client.aclose()
