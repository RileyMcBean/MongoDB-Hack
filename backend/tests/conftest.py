import certifi
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

TEST_DB_NAME = "access_agent_test"


@pytest_asyncio.fixture
async def test_db():
    client = AsyncIOMotorClient(settings.mongodb_uri, tlsCAFile=certifi.where())
    db = client[TEST_DB_NAME]
    yield db
    # Drop all collections (readWriteAnyDatabase doesn't allow dropDatabase)
    for col in await db.list_collection_names():
        await db[col].drop()
    client.close()
