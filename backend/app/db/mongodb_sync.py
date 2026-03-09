from pymongo import MongoClient
from pymongo.database import Database

from app.config import settings

_sync_client: MongoClient | None = None


def get_sync_mongo_client() -> MongoClient:
    global _sync_client
    if _sync_client is None:
        _sync_client = MongoClient(settings.mongodb_url)
    return _sync_client


def get_sync_mongo_db() -> Database:
    client = get_sync_mongo_client()
    return client[settings.mongodb_database]
