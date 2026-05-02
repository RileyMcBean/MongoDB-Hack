import pytest
from motor.motor_asyncio import AsyncIOMotorDatabase


@pytest.mark.asyncio
async def test_db_connection_returns_database(test_db):
    assert test_db is not None
    assert isinstance(test_db, AsyncIOMotorDatabase)


@pytest.mark.asyncio
async def test_db_can_list_collections(test_db):
    collections = await test_db.list_collection_names()
    assert isinstance(collections, list)
