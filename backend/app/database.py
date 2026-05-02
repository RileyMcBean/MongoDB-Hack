import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from .config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return _client[settings.db_name]


async def connect_db() -> None:
    global _client
    _client = AsyncIOMotorClient(settings.mongodb_uri, tlsCAFile=certifi.where())


async def close_db() -> None:
    global _client
    if _client:
        _client.close()
        _client = None
