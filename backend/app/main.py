 
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
    limit: Optional[int] = Query(None, ge=1, le=100000, description="Optional cap on number of rows"),
):
    coll = get_collection()
    q = {"date": {"$gte": start, "$lte": end}, "site": site}
    cursor = coll.find(q).sort("date", 1)
    if limit is not None:
        cursor = cursor.limit(int(limit))
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
    points: int = Query(100, ge=10, le=2000, description="Target number of points"),
):
    """Downsample metrics to ~points by uniform index-based binning.

    Behavior:
    - If available points n <= points: return daily values (no change)
    - Else: split the sorted series into contiguous windows and average within each
    This preserves detail better than coarse calendar bucketing while keeping payload bounded.
    """
    coll = get_collection()
    q = {"date": {"$gte": start, "$lte": end}, "site": site}

    # Count and short-circuit
    n = await coll.count_documents(q)
    if n == 0:
        return []

    # Fetch only necessary fields, sorted
    cursor = (
        coll
        .find(q, {"_id": 0, "date": 1, "fce": 1, "avg_temperature_C": 1})
        .sort("date", 1)
    )
    docs = await cursor.to_list(length=n)

    # If we already have <= desired points, return as-is with rounding
    if n <= points:
        out: list[dict] = []
        for d in docs:
            out.append({
                "date": d.get("date"),
                "fce": round(float(d.get("fce", 0.0)), 3),
                "avg_temperature_C": (
                    round(float(d.get("avg_temperature_C")), 3)
                    if d.get("avg_temperature_C") is not None else None
                ),
            })
        return out

    # Otherwise, average within ~equal-sized windows by index
    step = n / float(points)
    rebinned: list[dict] = []
    for i in range(points):
        start_idx = int(i * step)
        end_idx = int((i + 1) * step) - 1
        if end_idx < start_idx:
            end_idx = start_idx
        if end_idx >= n:
            end_idx = n - 1
        chunk = docs[start_idx:end_idx + 1]
        if not chunk:
            continue
        date_val = chunk[0].get("date")
        fce_avg = sum(float(x.get("fce", 0.0)) for x in chunk) / len(chunk)
        temps = [float(x.get("avg_temperature_C")) for x in chunk if x.get("avg_temperature_C") is not None]
        temp_avg = (sum(temps) / len(temps)) if temps else None
        rebinned.append({
            "date": date_val,
            "fce": round(fce_avg, 3),
            "avg_temperature_C": (round(temp_avg, 3) if temp_avg is not None else None),
        })

    return rebinned

