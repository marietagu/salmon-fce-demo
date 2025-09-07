from pydantic import BaseModel
import os

class Settings(BaseModel):
    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_db: str = os.getenv("MONGO_DB", "salmon_fce")
    mongo_coll: str = os.getenv("MONGO_COLL", "fce_daily")
    allowed_origins: list[str] = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    auth0_domain: str | None = os.getenv("AUTH0_DOMAIN")
    auth0_audience: str | None = os.getenv("AUTH0_AUDIENCE")
    auth_disabled: bool = os.getenv("AUTH_DISABLED", "true").lower() == "true"

settings = Settings()

