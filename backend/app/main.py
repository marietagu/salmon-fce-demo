 
from __future__ import annotations
from datetime import date
from typing import Optional, List
from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .db import get_collection
from .models import DailyRecord, SummaryResponse
from .security import verify_jwt

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
    _=Depends(verify_jwt),
):
    coll = get_collection()
    q = {"date": {"$gte": start, "$lte": end}, "site": site}
    cursor = coll.find(q).sort("date", 1).limit(limit)
    docs = [d async for d in cursor]
    for d in docs:
        d.pop("_id", None)
    return docs

@app.get("/api/metrics/latest", response_model=DailyRecord)
async def latest(site: str = Query("Marlborough Sounds"), _=Depends(verify_jwt)):
    coll = get_collection()
    d = await coll.find_one({"site": site}, sort=[("date", -1)])
    d.pop("_id", None)
    return d

@app.get("/api/summary", response_model=SummaryResponse)
async def summary(
    start: str = Query(...),
    end: str = Query(...),
    site: str = Query("Marlborough Sounds"),
    _=Depends(verify_jwt),
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

