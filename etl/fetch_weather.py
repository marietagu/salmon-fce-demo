from __future__ import annotations
from datetime import date, timedelta
from typing import Dict
import httpx

OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/era5"

async def fetch_daily_mean_temp(lat: float, lon: float, start: date, days: int) -> Dict[str, float]:
    # Clamp end to today to avoid Open-Meteo 400s for future dates
    requested_end = start + timedelta(days=days - 1)
    today = date.today()
    end = requested_end if requested_end <= today else today
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
    # Some days may have nulls; allow None so downstream merge can proceed
    return {d: (float(t) if t is not None else None) for d, t in zip(dates, temps)}

