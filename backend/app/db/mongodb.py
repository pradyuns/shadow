from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

# module-level singleton — reused across all async requests
_client: AsyncIOMotorClient | None = None


def get_mongo_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongodb_url)
    return _client


def get_mongo_db() -> AsyncIOMotorDatabase:
    client = get_mongo_client()
    return client[settings.mongodb_database]


async def close_mongo_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


# replace mongo _id with a string id field for api responses
def normalize_mongo_id(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc
