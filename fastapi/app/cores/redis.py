import redis.asyncio as redis


def create_redis_pool(url: str, max_connection: int):
    pool = redis.ConnectionPool.from_url(
        url,
        max_connections=max_connection,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
        # socket_keepalive=True,
    )
    return pool
