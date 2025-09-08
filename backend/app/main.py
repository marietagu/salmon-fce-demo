 
from __future__ import annotations
from datetime import date
from typing import Optional, List
from math import ceil
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .db import get_collection
from .models import DailyRecord, SummaryResponse, AggregatedPoint
# Auth removed: all endpoints are public

app = FastAPI(title="FCE Demo API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/api/metrics", response_model=List[DailyRecord])
async def get_metrics(
    start: str = Query(..., description="YYYY-MM-DD"),
    end: str = Query(..., description="YYYY-MM-DD"),
    site: str = Query("Marlborough Sounds"),
    limit: int = Query(1000, le=2000),
):
    coll = get_collection()
    q = {"date": {"$gte": start, "$lte": end}, "site": site}
    cursor = coll.find(q).sort("date", 1).limit(limit)
    docs = [d async for d in cursor]
    for d in docs:
        d.pop("_id", None)
    return docs

@app.get("/api/metrics/latest", response_model=DailyRecord)
async def latest(site: str = Query("Marlborough Sounds")):
    coll = get_collection()
    d = await coll.find_one({"site": site}, sort=[("date", -1)])
    d.pop("_id", None)
    return d

@app.get("/api/summary", response_model=SummaryResponse)
async def summary(
    start: str = Query(...),
    end: str = Query(...),
    site: str = Query("Marlborough Sounds"),
):
    coll = get_collection()
    pipeline = [
        {"$match": {"date": {"$gte": start, "$lte": end}, "site": site}},
        {"$group": {
            "_id": None,
            "count": {"$sum": 1},
            "avg_fcr": {"$avg": "$fcr"},
            "avg_fce": {"$avg": "$fce"}
        }}
    ]
    agg = await coll.aggregate(pipeline).to_list(1)
    if not agg:
        return {"start": start, "end": end, "site": site, "count": 0, "avg_fcr": 0.0, "avg_fce": 0.0}
    a = agg[0]
    return {
        "start": start,
        "end": end,
        "site": site,
        "count": int(a.get("count", 0)),
        "avg_fcr": round(a.get("avg_fcr", 0.0), 3),
        "avg_fce": round(a.get("avg_fce", 0.0), 3),
    }

@app.get("/api/metrics/aggregated", response_model=List[AggregatedPoint])
async def get_metrics_aggregated(
    start: str = Query(..., description="YYYY-MM-DD"),
    end: str = Query(..., description="YYYY-MM-DD"),
    site: str = Query("Marlborough Sounds"),
    points: int = Query(100, ge=10, le=1000, description="Target number of points"),
):
    """Downsample metrics to ~points by bucketing by day/week/month.
    - < 60 days: daily (no change)
    - 60-240 days: weekly average
    - > 240 days: monthly average
    Returns representative points with date labels at bucket boundaries.
    """
    coll = get_collection()
    # Determine bucket key by date prefix
    span_pipeline = [
        {"$match": {"date": {"$gte": start, "$lte": end}, "site": site}},
        {"$sort": {"date": 1}},
        {"$group": {"_id": None, "min": {"$first": "$date"}, "max": {"$last": "$date"}, "n": {"$sum": 1}}},
    ]
    span = await coll.aggregate(span_pipeline).to_list(1)
    n = int(span[0]["n"]) if span else 0
    if n == 0:
        return []
    if n <= 60:
        group_key = "$date"  # daily
    elif n <= 240:
        group_key = {"$substr": ["$date", 0, 8]}  # YYYY-MM- (weekly approx via later bucket size)
    else:
        group_key = {"$substr": ["$date", 0, 7]}  # YYYY-MM (monthly)

    # If weekly, we will post-bucket 7-day windows by index; for monthly we use prefix.
    # Compute averages per bucket
    pipeline = [
        {"$match": {"date": {"$gte": start, "$lte": end}, "site": site}},
        {"$sort": {"date": 1}},
        {"$group": {
            "_id": group_key,
            "date": {"$first": "$date"},
            "fce": {"$avg": "$fce"},
            "avg_temperature_C": {"$avg": "$avg_temperature_C"},
        }},
        {"$sort": {"date": 1}},
    ]
    buckets = await coll.aggregate(pipeline).to_list(points * 3)

    # If n between 60 and 240, transform date prefix YYYY-MM- to weekly buckets of size ~n/points
    if n > 60 and n <= 240:
        # Re-bucket by index into ~points chunks
        step = max(1, ceil(len(buckets) / points))
        rebinned = []
        for i in range(0, len(buckets), step):
            chunk = buckets[i:i+step]
            if not chunk:
                continue
            date_val = chunk[0]["date"]
            fce_avg = sum(x.get("fce", 0.0) for x in chunk) / len(chunk)
            temps = [x.get("avg_temperature_C") for x in chunk if x.get("avg_temperature_C") is not None]
            temp_avg = (sum(temps) / len(temps)) if temps else None
            rebinned.append({"date": date_val, "fce": round(fce_avg, 3), "avg_temperature_C": (round(temp_avg, 3) if temp_avg is not None else None)})
        return rebinned[:points]

    # Otherwise daily or monthly buckets are already computed
    result = []
    for b in buckets:
        result.append({
            "date": b.get("date"),
            "fce": round(float(b.get("fce", 0.0)), 3),
            "avg_temperature_C": (round(float(b.get("avg_temperature_C")), 3) if b.get("avg_temperature_C") is not None else None),
        })
    # Downsample if still too many
    if len(result) > points:
        step = max(1, ceil(len(result) / points))
        result = result[::step][:points]
    return result

