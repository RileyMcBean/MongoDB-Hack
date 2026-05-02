import re
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from .repositories import DataAssetRepository


def _tokenize(text: str) -> set[str]:
    """Lowercase and split into words, stripping punctuation."""
    return set(re.findall(r"[a-z]+", text.lower()))


async def match_asset(db: AsyncIOMotorDatabase, raw_request: str) -> Optional[dict]:
    """Score each asset by tag/name overlap with the request. Return best match or None."""
    repo = DataAssetRepository(db)
    assets = await repo.find_all()
    if not assets:
        return None

    request_tokens = _tokenize(raw_request)
    best_asset = None
    best_score = 0

    for asset in assets:
        score = 0
        for tag in asset.get("tags", []):
            if tag.lower() in request_tokens:
                score += 2
        for word in _tokenize(asset.get("name", "")):
            if len(word) > 3 and word in request_tokens:
                score += 1
        for word in asset.get("collection_name", "").replace("_", " ").split():
            if word.lower() in request_tokens:
                score += 1

        if score > best_score:
            best_score = score
            best_asset = asset

    return best_asset if best_score > 0 else None
