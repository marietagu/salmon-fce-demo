from pydantic import BaseModel, Field
from typing import Optional

class DailyRecord(BaseModel):
    date: str
    site: str
    feed_given_kg: float
    biomass_gain_kg: float
    fcr: float
    fce: float
    health_score: float
    avg_temperature_C: Optional[float] = None
    regime: str = Field(pattern=r"^(normal|reduced)$")

class SummaryResponse(BaseModel):
    start: str
    end: str
    site: str
    count: int
    avg_fcr: float
    avg_fce: float

class AggregatedPoint(BaseModel):
    date: str
    fce: float
    avg_temperature_C: Optional[float] = None

