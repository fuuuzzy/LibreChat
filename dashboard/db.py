from motor.motor_asyncio import AsyncIOMotorClient
import config

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(config.MONGO_URI)
    return _client


def get_db():
    return get_client()[config.DB_NAME]


def close():
    global _client
    if _client:
        _client.close()
        _client = None
