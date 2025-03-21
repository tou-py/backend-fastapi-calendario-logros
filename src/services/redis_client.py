import redis.asyncio as redis
from src.config import settings


class RedisClient:
    def __init__(
        self, redis_url: str = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
    ):
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)

    async def set(self, key: str, value: str, ex: int = None):
        await self.redis.set(key, value, ex=ex)

    async def get(self, key: str):
        return await self.redis.get(key)

    async def delete(self, key: str):
        await self.redis.delete(key)

    async def close(self):
        await self.redis.close()
