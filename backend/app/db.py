from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

client: AsyncIOMotorClient | None = None

def get_collection():
    global client
    if client is None:
        client = AsyncIOMotorClient(settings.mongo_uri)
    return client[settings.mongo_db][settings.mongo_coll]

