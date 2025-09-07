from __future__ import annotations
import asyncio
import os
from datetime import date

from generate_synthetic import generate_daily_records
from fetch_weather import fetch_daily_mean_temp
from merge_and_load import merge_and_upsert

# Defaults for local dev
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB = os.getenv("MONGO_DB", "salmon_fce")
COLL = os.getenv("MONGO_COLL", "fce_daily")
SITE = os.getenv("SITE_NAME", "Marlborough Sounds")
LAT = float(os.getenv("OPEN_METEO_LAT", "-41.2706"))  # Nelson approx
LON = float(os.getenv("OPEN_METEO_LON", "173.2840"))
START = date.fromisoformat(os.getenv("SEED_START", f"{date.today().year-1}-09-01"))
DAYS = int(os.getenv("SEED_DAYS", "365"))

async def main():
    print(f"Generating synthetic for {DAYS} days from {START} at {SITE}")
    records = list(generate_daily_records(START, DAYS, SITE))
    temps = await fetch_daily_mean_temp(LAT, LON, START, DAYS)
    await merge_and_upsert(records, temps, MONGO_URI, DB, COLL)
    print("Seed complete")

if __name__ == "__main__":
    asyncio.run(main())

