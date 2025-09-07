from __future__ import annotations
from typing import Iterable, Dict
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne

async def merge_and_upsert(records: Iterable[Dict], temps_by_date: Dict[str, float], mongo_uri: str, db: str, coll: str):
    client = AsyncIOMotorClient(mongo_uri)
    collection = client[db][coll]
    # index
    await collection.create_index([("date", 1), ("site", 1)], unique=True)

    docs = []
    for rec in records:
        rec["avg_temperature_C"] = temps_by_date.get(rec["date"])  # may be None; acceptable for demo
        docs.append(rec)

    # bulk upsert by (date, site)
    ops = []
    for d in docs:
        filt = {"date": d["date"], "site": d["site"]}
        ops.append(UpdateOne(filt, {"$set": d}, upsert=True))
    if ops:
        await collection.bulk_write(ops, ordered=False)

