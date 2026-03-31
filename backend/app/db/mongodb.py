from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

# module-level singleton — reused across all async requests
_client: AsyncIOMotorClient[dict[str, Any]] | None = None


def get_mongo_client() -> AsyncIOMotorClient[dict[str, Any]]:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongodb_url)
    return _client


def get_mongo_db() -> AsyncIOMotorDatabase[dict[str, Any]]:
    client = get_mongo_client()
    return client[settings.mongodb_database]


async def close_mongo_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


# replace mongo _id with a string id field for api responses
def normalize_mongo_id(doc: dict[str, Any]) -> dict[str, Any]:
    doc["id"] = str(doc.pop("_id"))
    return doc
