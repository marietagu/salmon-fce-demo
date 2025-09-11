from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

client: AsyncIOMotorClient | None = None

def get_collection():
    global client
    if client is None:
        client = AsyncIOMotorClient(settings.mongo_uri)
    return client[settings.mongo_db][settings.mongo_coll]

async def ensure_indexes() -> None:
    """Create required indexes if they do not already exist.

    We index by (site asc, date asc) to support queries that filter by site and
    date range and then sort by date ascending. This dramatically reduces RU and
    latency for range queries used by the charts.
    """
    coll = get_collection()
    try:
        await coll.create_index([("site", 1), ("date", 1)], name="site_date_asc")
    except Exception:
        # Index creation is idempotent. Ignore errors in read-only or limited
        # permission environments to avoid failing app startup.
        pass

