import redis.asyncio as redis
from fastapi import Depends, Request


def get_redis_pool(req: Request):
    return req.app.state.redis_pool


async def get_redis_client(pool: redis.ConnectionPool = Depends(get_redis_pool)):
    client = redis.Redis(connection_pool=pool)
    try:
        yield client
    finally:
        await client.aclose()
