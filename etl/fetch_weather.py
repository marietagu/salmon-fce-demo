from __future__ import annotations
from datetime import date, timedelta
from typing import Dict
import httpx

OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/era5"

async def fetch_daily_mean_temp(lat: float, lon: float, start: date, days: int) -> Dict[str, float]:
    end = start + timedelta(days=days - 1)
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "temperature_2m_mean",
        "timezone": "UTC",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(OPEN_METEO_URL, params=params)
        r.raise_for_status()
        data = r.json()
    dates = data.get("daily", {}).get("time", [])
    temps = data.get("daily", {}).get("temperature_2m_mean", [])
    return {d: float(t) for d, t in zip(dates, temps)}

