import json
from redis.asyncio import Redis
from db.clients.redis import RedisServices

CACHE_TTL = 60


class ProjectCache:
    KEY_PREFIX = "project:list"

    @classmethod
    def _key(cls, user_id: int) -> str:
        return f"{cls.KEY_PREFIX}:{user_id}"

    @classmethod
    def get_redis(cls) -> Redis:
        return RedisServices.get_redis_client()

    @classmethod
    async def get(cls, user_id: int) -> list | None:
        redis = cls.get_redis()
        raw = await redis.get(cls._key(user_id))
        if raw is None:
            return None
        return json.loads(raw)

    @classmethod
    async def set(cls, user_id: int, data: list) -> None:
        redis = cls.get_redis()
        await redis.set(cls._key(user_id), json.dumps(data), ex=CACHE_TTL)

    @classmethod
    async def invalidate(cls, user_id: int) -> None:
        redis = cls.get_redis()
        await redis.delete(cls._key(user_id))