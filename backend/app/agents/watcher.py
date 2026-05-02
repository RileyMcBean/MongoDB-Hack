"""
Change stream watcher — monitors users and data_assets collections.
When a change is detected the LLM writes a semantic memory so agents
have up-to-date context on the next request.
"""
import asyncio
import logging
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..repositories import MemoryEntryRepository
from ..models import MemoryEntry, MemoryType
from .embeddings import embed_text

logger = logging.getLogger(__name__)


def _get_llm():
    from langchain_fireworks import ChatFireworks
    return ChatFireworks(
        model="accounts/fireworks/models/llama-v3p3-70b-instruct",
        api_key=os.environ.get("FIREWORKS_API_KEY", ""),
        temperature=0,
    )


async def _write_semantic_memory(db: AsyncIOMotorDatabase, content: str, tags: list[str]):
    try:
        embedding = await embed_text(content)
        await MemoryEntryRepository(db).insert(MemoryEntry(
            type=MemoryType.semantic,
            content=content,
            tags=tags,
            embedding=embedding,
        ))
        logger.info(f"Semantic memory written: {content[:80]}...")
    except Exception as e:
        logger.error(f"Failed to write semantic memory: {e}")


async def _summarise_change(operation: str, collection: str, doc: dict) -> str:
    """Ask the LLM to write a one-sentence semantic memory about a change."""
    import json
    # Remove MongoDB internals before sending to LLM
    clean = {k: v for k, v in doc.items() if k not in ("_id",)}
    prompt = f"""A '{operation}' event occurred in the '{collection}' collection of a data governance system.

Document: {json.dumps(clean, default=str)}

Write ONE sentence describing what changed and why it matters for future access requests.
Be specific. No fluff."""
    try:
        llm = _get_llm()
        return llm.invoke(prompt).content.strip()
    except Exception as e:
        logger.error(f"Watcher LLM summarise failed: {e}")
        return f"{operation} detected in {collection}: {list(clean.keys())}"


async def _watch_collection(db: AsyncIOMotorDatabase, collection_name: str):
    """Watch a single collection and write semantic memories on changes."""
    col = db[collection_name]
    logger.info(f"Change stream watcher started on '{collection_name}'")
    try:
        async with col.watch(full_document="updateLookup") as stream:
            async for change in stream:
                op = change.get("operationType", "unknown")
                if op not in ("insert", "update", "replace"):
                    continue
                doc = change.get("fullDocument") or {}
                summary = await _summarise_change(op, collection_name, doc)
                # Tags: collection name + key fields
                tags = [collection_name, op]
                if "username" in doc:
                    tags.append(doc["username"])
                if "name" in doc:
                    tags.append(doc["name"])
                await _write_semantic_memory(db, summary, tags)
    except Exception as e:
        logger.error(f"Change stream on '{collection_name}' crashed: {e}")


async def start_watchers(db: AsyncIOMotorDatabase):
    """
    Start background change stream watchers on users and data_assets.
    Returns immediately — watchers run as asyncio tasks.
    """
    asyncio.create_task(_watch_collection(db, "users"))
    asyncio.create_task(_watch_collection(db, "data_assets"))
    logger.info("Change stream watchers started for users + data_assets")
