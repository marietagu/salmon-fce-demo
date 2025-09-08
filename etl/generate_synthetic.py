from __future__ import annotations
import math
import random
import hashlib
from datetime import date, timedelta
from typing import Iterable, Dict


def _rng_for_day(d: date, site: str, seed: int | None) -> random.Random:
    """Create a deterministic RNG anchored to calendar date and site.

    Using sha256 ensures stability across interpreter runs.
    """
    salt = str(seed) if seed is not None else "0"
    h = hashlib.sha256(f"{site}|{d.isoformat()}|{salt}".encode("utf-8")).digest()
    # Use first 8 bytes to seed a local RNG
    return random.Random(int.from_bytes(h[:8], "big", signed=False))


def generate_daily_records(
    start: date,
    days: int,
    site: str = "Marlborough Sounds",
    seed: int | None = 42,
) -> Iterable[Dict]:
    """Generate deterministic daily records anchored to calendar dates.

    - Randomness is derived from (site, date, seed)
    - Seasonality depends on the day-of-year, not the chunk index
    This makes the generator chunk-safe and idempotent across re-runs.
    """
    biomass = 10000.0  # kg, starting cohort (used only for running total)
    for i in range(days):
        d = start + timedelta(days=i)
        rng = _rng_for_day(d, site, seed)

        # Regime: reduced feeding during a fixed seasonal window (DOY 120-160)
        yday = d.timetuple().tm_yday
        regime = "reduced" if 120 <= yday <= 160 else "normal"

        # Base feed and gain with deterministic per-day stochasticity
        base_feed = 500.0 if regime == "normal" else 380.0
        feed_given = max(0.0, rng.gauss(base_feed, base_feed * 0.07))

        # Efficiency varies with a gentle seasonal pattern using calendar day
        seasonal = 0.1 * math.sin(2 * math.pi * (yday / 365.25))  # [-0.1, 0.1]
        efficiency = 0.35 + seasonal
        efficiency *= (0.9 if regime == "reduced" else 1.0)
        efficiency = max(0.05, min(efficiency, 0.6))

        biomass_gain = max(0.001, feed_given * efficiency)
        fcr = feed_given / biomass_gain if biomass_gain > 0 else float("inf")
        fce = 1.0 / fcr if fcr > 0 else 0.0

        # Health score heuristic (higher with better efficiency)
        health_score = max(0.0, min(100.0, 60 + (fce - 0.4) * 200 + rng.gauss(0, 5)))

        biomass += biomass_gain

        yield {
            "date": d.isoformat(),
            "site": site,
            "feed_given_kg": round(feed_given, 2),
            "biomass_gain_kg": round(biomass_gain, 2),
            "fcr": round(fcr, 3),
            "fce": round(fce, 3),
            "health_score": round(health_score, 1),
            "regime": regime,
        }

