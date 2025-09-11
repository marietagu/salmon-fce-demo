from __future__ import annotations
from datetime import date, timedelta
from typing import Dict
import httpx

# Archive reanalysis (lagging by 1-3 days)
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/era5"
# Forecast API (provides recent past + today). We'll use it to backfill recent missing days.
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

async def fetch_daily_mean_temp(lat: float, lon: float, start: date, days: int) -> Dict[str, float | None]:
    """Return map of ISO date -> daily mean temperature.

    Strategy:
    - Query ERA5 archive for the full requested range (clamped to today)
    - If recent days are missing (common due to ERA5 latency), query forecast API
      for last ~7 days + today and fill gaps. Use Pacific/Auckland timezone to
      ensure "today" aligns for NZ users.
    """
    requested_end = start + timedelta(days=days - 1)
    today = date.today()
    end = requested_end if requested_end <= today else today

    # Initialize output with None for all requested dates up to end (inclusive)
    dates_full = [
        (start + timedelta(days=i)).isoformat()
        for i in range(days)
        if (start + timedelta(days=i)) <= end
    ]
    out: Dict[str, float | None] = {d: None for d in dates_full}

    # 1) Archive (ERA5)
    params_archive = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "temperature_2m_mean",
        "timezone": "UTC",
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(OPEN_METEO_ARCHIVE_URL, params=params_archive)
            r.raise_for_status()
            data = r.json()
        dates = data.get("daily", {}).get("time", [])
        temps = data.get("daily", {}).get("temperature_2m_mean", [])
        for d, t in zip(dates, temps):
            if d in out:
                out[d] = float(t) if t is not None else None
    except (httpx.RequestError, httpx.HTTPStatusError):
        # If archive fails, we will try to fill recent days via forecast below
        pass

    # 2) Fill recent missing days with forecast (last 7 days + today)
    recent_start = today - timedelta(days=6)
    needs_recent = any((date.fromisoformat(d) >= recent_start and out[d] is None) for d in out)
    if needs_recent:
        params_forecast = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_mean",
            # Use NZ timezone so "today" is included for NZ users
            "timezone": "Pacific/Auckland",
            "past_days": 7,
            "forecast_days": 2,
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r2 = await client.get(OPEN_METEO_FORECAST_URL, params=params_forecast)
                r2.raise_for_status()
                d2 = r2.json()
            f_times = d2.get("daily", {}).get("time", [])
            f_vals = d2.get("daily", {}).get("temperature_2m_mean", [])
            f_map = {d: (float(t) if t is not None else None) for d, t in zip(f_times, f_vals)}
            for d in out:
                if out[d] is None and d in f_map:
                    out[d] = f_map[d]
        except (httpx.RequestError, httpx.HTTPStatusError):
            # If forecast also fails, we keep None for recent dates
            pass

    return out

