from __future__ import annotations
import os
import asyncio
from datetime import date, timedelta
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient

from generate_synthetic import generate_daily_records
from fetch_weather import fetch_daily_mean_temp
from merge_and_load import merge_and_upsert


MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB = os.getenv("MONGO_DB", "salmon_fce")
COLL = os.getenv("MONGO_COLL", "fce_daily")
SITE = os.getenv("SITE_NAME", "Marlborough Sounds")
LAT = float(os.getenv("OPEN_METEO_LAT", "-41.2706"))
LON = float(os.getenv("OPEN_METEO_LON", "173.2840"))


async def _latest_date_for_site(client: AsyncIOMotorClient, site: str) -> Optional[date]:
    coll = client[DB][COLL]
    doc = await coll.find_one({"site": site}, sort=[("date", -1)])
    if not doc or not doc.get("date"):
        return None
    return date.fromisoformat(doc["date"])


async def main() -> None:
    client = AsyncIOMotorClient(MONGO_URI)

    latest = await _latest_date_for_site(client, SITE)
    if latest is None:
        # Fallback to last year's season start if DB is empty
        start = date.fromisoformat(f"{date.today().year-1}-09-01")
    else:
        start = latest + timedelta(days=1)

    today = date.today()
    if start > today:
        print("Up to date; no new days to seed")
        return

    days = (today - start).days + 1
    print(f"Top-up seeding from {start} for {days} days at {SITE}")

    records = list(generate_daily_records(start, days, SITE))
    temps = await fetch_daily_mean_temp(LAT, LON, start, days)
    await merge_and_upsert(records, temps, MONGO_URI, DB, COLL)
    print("Top-up complete")


if __name__ == "__main__":
    asyncio.run(main())


