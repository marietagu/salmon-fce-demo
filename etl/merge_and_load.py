from __future__ import annotations
from typing import Iterable, Dict
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError

async def merge_and_upsert(records: Iterable[Dict], temps_by_date: Dict[str, float], mongo_uri: str, db: str, coll: str):
    client = AsyncIOMotorClient(mongo_uri)
    collection = client[db][coll]
    # index
    await collection.create_index([("date", 1), ("site", 1)], unique=True)

    docs = []
    for rec in records:
        rec["avg_temperature_C"] = temps_by_date.get(rec["date"])  # may be None; acceptable for demo
        docs.append(rec)

    # bulk upsert by (date, site) with throttling/backoff for Cosmos RU limits
    ops = []
    for d in docs:
        filt = {"date": d["date"], "site": d["site"]}
        ops.append(UpdateOne(filt, {"$set": d}, upsert=True))

    async def write_with_backoff(batched_ops: list[UpdateOne], *, max_retries: int = 6) -> None:
        attempt = 0
        delay_seconds = 0.5
        while True:
            try:
                await collection.bulk_write(batched_ops, ordered=False)
                return
            except BulkWriteError:
                attempt += 1
                if attempt >= max_retries:
                    raise
                await asyncio.sleep(delay_seconds)
                delay_seconds = min(delay_seconds * 2, 10.0)

    if ops:
        batch_size = 25
        for i in range(0, len(ops), batch_size):
            batch = ops[i : i + batch_size]
            await write_with_backoff(batch)
            # brief pacing between batches to avoid 429s
            await asyncio.sleep(0.25)

