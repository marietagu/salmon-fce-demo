from pydantic import BaseModel
import os
from typing import Optional

def _parse_allowed_origins(default_csv: str) -> list[str]:
    raw = os.getenv("ALLOWED_ORIGINS", default_csv)
    parts = [p.strip() for p in raw.split(",")]
    # normalize by dropping trailing slashes and removing empties
    return [p.rstrip("/") for p in parts if p]

class Settings(BaseModel):
    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_db: str = os.getenv("MONGO_DB", "salmon_fce")
    mongo_coll: str = os.getenv("MONGO_COLL", "fce_daily")
    allowed_origins: list[str] = _parse_allowed_origins("http://localhost:5173")
    # Optional regex for wildcard hostnames (e.g., ".*\\.contoso\\.com$")
    allowed_origin_regex: Optional[str] = os.getenv("ALLOWED_ORIGIN_REGEX")
    # Auth removed; keep flag but default to true for public API
    auth_disabled: bool = True

settings = Settings()

