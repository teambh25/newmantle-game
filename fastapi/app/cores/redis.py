from fastapi import Request
import redis.asyncio as redis

def create_redis_pool(redis_url:str, max_connection: int):
    pool = redis.ConnectionPool.from_url(
        redis_url,
        max_connections=max_connection,
        decode_responses=True
    )
    return pool


async def get_redis_client(req: Request):
    client = redis.Redis(connection_pool=req.app.state.redis_pool)
    try:
        yield client
    finally:
        await client.aclose()