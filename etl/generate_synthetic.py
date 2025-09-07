from __future__ import annotations
import math
import random
from datetime import date, timedelta
from typing import Iterable, Dict

random.seed(42)

def generate_daily_records(start: date, days: int, site: str = "Marlborough Sounds", seed: int | None = 42) -> Iterable[Dict]:
    if seed is not None:
        random.seed(seed)
    biomass = 10000.0  # kg, starting cohort
    for i in range(days):
        d = start + timedelta(days=i)
        # Regime: reduced feeding between day 120-160
        regime = "reduced" if 120 <= i <= 160 else "normal"

        # Base feed and gain with some stochasticity
        base_feed = 500.0 if regime == "normal" else 380.0
        feed_given = max(0.0, random.gauss(base_feed, base_feed * 0.07))

        # Efficiency varies with a gentle seasonal pattern (proxy for temp influence)
        seasonal = 0.1 * math.sin(2 * math.pi * (i / 365.0))  # [-0.1, 0.1]
        efficiency = 0.35 + seasonal  # nominal feed->gain efficiency
        efficiency *= (0.9 if regime == "reduced" else 1.0)
        efficiency = max(0.05, min(efficiency, 0.6))

        biomass_gain = max(0.001, feed_given * efficiency)
        fcr = feed_given / biomass_gain if biomass_gain > 0 else float("inf")
        fce = 1.0 / fcr if fcr > 0 else 0.0

        # Health score heuristic (higher with better efficiency)
        health_score = max(0.0, min(100.0, 60 + (fce - 0.4) * 200 + random.gauss(0, 5)))

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

