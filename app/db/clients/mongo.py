from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from core.config import settings


class MongodbServices:
    _client: AsyncIOMotorClient | None = None
    _db: AsyncIOMotorDatabase | None = None

    @classmethod
    def get_client(cls) -> AsyncIOMotorClient:
        if cls._client is None:
            cls._client = AsyncIOMotorClient(
                settings.mongo_uri,
                maxPoolSize=50,
                minPoolSize=1,
                serverSelectionTimeoutMS=5000,
                uuidRepresentation="standard",
            )
        return cls._client

    @classmethod
    def get_mongo_db(cls) -> AsyncIOMotorDatabase:
        if cls._db is None:
            cls._db = cls.get_client()[settings.mongo_db_name]
        return cls._db

    @classmethod
    async def close(cls) -> None:
        if cls._client is not None:
            cls._client.close()
            cls._client = None
            cls._db = None