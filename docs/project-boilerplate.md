Below is a ready‑to‑paste scaffold. Copy the tree, create files, and you can run locally or with Docker Compose. Commented sections show where to customise.

---

## File tree

```
root/
  Makefile
  docker-compose.yml
  .gitignore
  .dockerignore
  .env.example
  README.md

  etl/
    __init__.py
    generate_synthetic.py
    fetch_weather.py
    merge_and_load.py
    seed.py

  backend/
    Dockerfile
    pyproject.toml
    app/
      __init__.py
      config.py
      db.py
      models.py
      security.py
      main.py

  frontend/
    Dockerfile
    index.html
    package.json
    vite.config.js
    src/
      main.jsx
      App.jsx
      components/
        Charts.jsx
      lib/
        api.js
        auth.js
    .env.example
```

---

## Makefile

```makefile
# ---- Makefile: quick dev commands ----
.PHONY: help dev api web seed compose-up compose-down lint test fmt

help:
	@echo "Targets:\n\
\tdev           - run backend (uvicorn) and frontend (vite) locally\n\
\tapi           - run FastAPI locally\n\
\tweb           - run React dev server\n\
\tseed          - generate + load 365d into Mongo (local)\n\
\tcompose-up    - docker compose up --build\n\
\tcompose-down  - docker compose down -v\n\
\tlint          - ruff lint (backend)\n\
\tfmt           - black format (backend)\n\
\ttest          - pytest (backend)\n"

# Backend local (requires Python 3.11, uv or pip, and Mongo running at mongodb://localhost:27017)
api:
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 || \
	( \
		python -m pip install -U pip && \
		python -m pip install -r <(python -c "import tomllib,sys;print('\n'.join(tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']))") && \
		uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 \
	)

# Frontend local dev
web:
	cd frontend && npm install && npm run dev

# One-shot seed using local Python (prefers uv). Requires Mongo at mongodb://localhost:27017
seed:
	cd etl && (uv run python seed.py || python seed.py)

# Run full stack in Docker (Mongo + API + Frontend)
compose-up:
	docker compose up --build

compose-down:
	docker compose down -v

lint:
	cd backend && uv run ruff check app || (python -m pip install ruff && ruff check app)

fmt:
	cd backend && uv run black app || (python -m pip install black && black app)

test:
	cd backend && uv run pytest || (python -m pip install pytest && pytest)
```

---

## docker-compose.yml

```yaml
version: "3.9"
services:
  mongo:
    image: mongo:7
    container_name: mongo
    restart: unless-stopped
    ports: ["27017:27017"]
    volumes:
      - mongo_data:/data/db

  api:
    build: ./backend
    container_name: fce-api
    depends_on: [mongo]
    environment:
      MONGO_URI: mongodb://mongo:27017
      MONGO_DB: salmon_fce
      MONGO_COLL: fce_daily
      ALLOWED_ORIGINS: http://localhost:5173,http://localhost:4173
      AUTH0_DOMAIN: ${AUTH0_DOMAIN:-}
      AUTH0_AUDIENCE: ${AUTH0_AUDIENCE:-}
      AUTH_DISABLED: ${AUTH_DISABLED:-true}
    ports: ["8000:8000"]
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

  web:
    build: ./frontend
    container_name: fce-web
    depends_on: [api]
    environment:
      VITE_API_BASE_URL: http://localhost:8000
      VITE_AUTH0_DOMAIN: ${VITE_AUTH0_DOMAIN:-}
      VITE_AUTH0_CLIENT_ID: ${VITE_AUTH0_CLIENT_ID:-}
      VITE_AUTH0_AUDIENCE: ${VITE_AUTH0_AUDIENCE:-}
    ports: ["5173:5173", "4173:4173"]
    # dev server on 5173; preview on 4173

volumes:
  mongo_data:
```

---

## .gitignore

```
# general
.DS_Store
node_modules/
*.log
.env
.env.*

# python
.venv/
__pycache__/
*.pyc

# build
frontend/dist/
backend/.pytest_cache/
```

## .dockerignore

```
**/.venv
**/__pycache__
**/*.pyc
node_modules
.git
.gitignore
frontend/dist
```

## .env.example (root)

```
# Backend/Auth0
AUTH0_DOMAIN=your-tenant.region.auth0.com
AUTH0_AUDIENCE=https://fce-demo-api
AUTH_DISABLED=true

# Frontend/Auth0
VITE_AUTH0_DOMAIN=your-tenant.region.auth0.com
VITE_AUTH0_CLIENT_ID=your-client-id
VITE_AUTH0_AUDIENCE=https://fce-demo-api

# API base (frontend)
VITE_API_BASE_URL=http://localhost:8000
```

---

# ETL

### etl/**init**.py

```python
# empty on purpose
```

### etl/generate\_synthetic.py

```python
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
```

### etl/fetch\_weather.py

```python
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
```

### etl/merge\_and\_load.py

```python
from __future__ import annotations
from typing import Iterable, Dict
from motor.motor_asyncio import AsyncIOMotorClient

async def merge_and_upsert(records: Iterable[Dict], temps_by_date: Dict[str, float], mongo_uri: str, db: str, coll: str):
    client = AsyncIOMotorClient(mongo_uri)
    collection = client[db][coll]
    # index
    await collection.create_index([("date", 1), ("site", 1)], unique=True)

    docs = []
    for rec in records:
        rec["avg_temperature_C"] = temps_by_date.get(rec["date"])  # may be None; acceptable for demo
        docs.append(rec)

    # bulk upsert by (date, site)
    ops = []
    for d in docs:
        filt = {"date": d["date"], "site": d["site"]}
        ops.append(
            {"update_one": {"filter": filt, "update": {"$set": d}, "upsert": True}}
        )
    if ops:
        await collection.bulk_write(ops, ordered=False)
```

### etl/seed.py

```python
from __future__ import annotations
import asyncio
import os
from datetime import date

from generate_synthetic import generate_daily_records
from fetch_weather import fetch_daily_mean_temp
from merge_and_load import merge_and_upsert

# Defaults for local dev
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB = os.getenv("MONGO_DB", "salmon_fce")
COLL = os.getenv("MONGO_COLL", "fce_daily")
SITE = os.getenv("SITE_NAME", "Marlborough Sounds")
LAT = float(os.getenv("OPEN_METEO_LAT", "-41.2706"))  # Nelson approx
LON = float(os.getenv("OPEN_METEO_LON", "173.2840"))
START = date.fromisoformat(os.getenv("SEED_START", f"{date.today().year-1}-09-01"))
DAYS = int(os.getenv("SEED_DAYS", "365"))

async def main():
    print(f"Generating synthetic for {DAYS} days from {START} at {SITE}")
    records = list(generate_daily_records(START, DAYS, SITE))
    temps = await fetch_daily_mean_temp(LAT, LON, START, DAYS)
    await merge_and_upsert(records, temps, MONGO_URI, DB, COLL)
    print("Seed complete")

if __name__ == "__main__":
    asyncio.run(main())
```

---

# Backend

### backend/pyproject.toml

```toml
[project]
name = "fce-backend"
version = "0.1.0"
description = "FastAPI backend for salmon FCE demo"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.114.0",
  "uvicorn[standard]>=0.30.0",
  "motor>=3.4.0",
  "pydantic>=2.8.2",
  "python-jose[cryptography]>=3.3.0",
  "httpx>=0.27.0",
  "structlog>=24.1.0",
  "pytest>=8.2.0",
]

[tool.black]
line-length = 100

[tool.ruff]
line-length = 100
```

### backend/Dockerfile

```dockerfile
# ---- build runtime ----
FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir uv && uv pip install --system -r <(python - <<'PY' \
import tomllib,sys;print('\n'.join(tomllib.load(open('pyproject.toml','rb'))['project']['dependencies'])) \
PY
)
COPY app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### backend/app/config.py

```python
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
```

### backend/app/db.py

```python
from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

client: AsyncIOMotorClient | None = None

def get_collection():
    global client
    if client is None:
        client = AsyncIOMotorClient(settings.mongo_uri)
    return client[settings.mongo_db][settings.mongo_coll]
```

### backend/app/models.py

```python
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
```

### backend/app/security.py

```python
from __future__ import annotations
import json
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
import httpx
from .config import settings

http_bearer = HTTPBearer(auto_error=False)
_jwks_cache: Optional[dict] = None

async def _get_jwks():
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    if not settings.auth0_domain:
        return None
    url = f"https://{settings.auth0_domain}/.well-known/jwks.json"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        return _jwks_cache

async def verify_jwt(creds: HTTPAuthorizationCredentials = Depends(http_bearer)):
    if settings.auth_disabled:
        return None
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    token = creds.credentials
    jwks = await _get_jwks()
    if not jwks:
        raise HTTPException(status_code=500, detail="JWKS unavailable")
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if not key:
        raise HTTPException(status_code=401, detail="Invalid token header")
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=[key.get("alg", "RS256")],
            audience=settings.auth0_audience,
            issuer=f"https://{settings.auth0_domain}/",
        )
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token invalid: {e}")
```

### backend/app/main.py

```python
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
```

---

# Frontend (Vite + React + Recharts)

### frontend/Dockerfile

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci || npm i
COPY . .
RUN npm run build

# Use vite preview for simplicity
EXPOSE 5173 4173
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "4173"]
```

### frontend/package.json

```json
{
  "name": "fce-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "@auth0/auth0-react": "^2.2.4",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "recharts": "^2.12.7",
    "@tanstack/react-query": "^5.51.1"
  },
  "devDependencies": {
    "vite": "^5.4.0",
    "@vitejs/plugin-react": "^4.2.0",
    "tailwindcss": "^3.4.9",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.41"
  }
}
```

### frontend/vite.config.js

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig({ plugins: [react()] })
```

### frontend/index.html

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>FCE Demo</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

### frontend/.env.example

```
VITE_API_BASE_URL=http://localhost:8000
VITE_AUTH0_DOMAIN=your-tenant.region.auth0.com
VITE_AUTH0_CLIENT_ID=your-client-id
VITE_AUTH0_AUDIENCE=https://fce-demo-api
```

### frontend/src/main.jsx

```jsx
import React from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'

const qc = new QueryClient()
createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
)
```

### frontend/src/lib/auth.js

```jsx
import React from 'react'
import { Auth0Provider, useAuth0 } from '@auth0/auth0-react'

export const AuthProvider = ({ children }) => (
  <Auth0Provider
    domain={import.meta.env.VITE_AUTH0_DOMAIN}
    clientId={import.meta.env.VITE_AUTH0_CLIENT_ID}
    authorizationParams={{
      audience: import.meta.env.VITE_AUTH0_AUDIENCE,
      redirect_uri: window.location.origin,
    }}
    cacheLocation="localstorage"
  >
    {children}
  </Auth0Provider>
)

export const useToken = () => {
  const { getAccessTokenSilently } = useAuth0()
  return async () => {
    if (!import.meta.env.VITE_AUTH0_DOMAIN) return null
    try { return await getAccessTokenSilently() } catch { return null }
  }
}
```

### frontend/src/lib/api.js

```js
export const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export async function fetchJSON(path, token) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}
```

### frontend/src/components/Charts.jsx

```jsx
import React from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid } from 'recharts'

export function FceChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" tickFormatter={(d)=>d.slice(5)} />
        <YAxis yAxisId="left" />
        <Tooltip />
        <Legend />
        <Line yAxisId="left" type="monotone" dataKey="fce" name="FCE" dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}

export function TempChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" tickFormatter={(d)=>d.slice(5)} />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="avg_temperature_C" name="Avg Temp (°C)" dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}
```

### frontend/src/App.jsx

```jsx
import React, { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AuthProvider, useToken } from './lib/auth'
import { fetchJSON } from './lib/api'
import { FceChart, TempChart } from './components/Charts'
import { useAuth0 } from '@auth0/auth0-react'

function Dashboard() {
  const today = useMemo(()=> new Date(), [])
  const startDefault = new Date(today); startDefault.setMonth(today.getMonth()-3)
  const [start, setStart] = useState(startDefault.toISOString().slice(0,10))
  const [end, setEnd] = useState(today.toISOString().slice(0,10))
  const [site, setSite] = useState('Marlborough Sounds')
  const getToken = useToken()

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['metrics', start, end, site],
    queryFn: async () => {
      const token = await getToken()
      return fetchJSON(`/api/metrics?start=${start}&end=${end}&site=${encodeURIComponent(site)}`, token)
    }
  })

  const { loginWithRedirect, logout, isAuthenticated } = useAuth0()

  return (
    <div style={{ maxWidth: 1000, margin: '20px auto', fontFamily: 'Inter, system-ui, sans-serif' }}>
      <header style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
        <h1>Salmon FCE Demo</h1>
        <div>
          {isAuthenticated ? (
            <button onClick={()=>logout({ logoutParams: { returnTo: window.location.origin }})}>Logout</button>
          ) : (
            <button onClick={()=>loginWithRedirect()}>Login</button>
          )}
        </div>
      </header>

      <section style={{ display:'grid', gap:12, gridTemplateColumns:'1fr 1fr 1fr' }}>
        <label>Start <input type="date" value={start} onChange={e=>setStart(e.target.value)} /></label>
        <label>End <input type="date" value={end} onChange={e=>setEnd(e.target.value)} /></label>
        <label>Site <input value={site} onChange={e=>setSite(e.target.value)} /></label>
      </section>

      <button onClick={()=>refetch()} style={{ marginTop: 10 }}>Refresh</button>

      {isLoading && <p>Loading…</p>}
      {error && <p>Error: {String(error)}</p>}

      {data && data.length>0 && (
        <>
          <FceChart data={data} />
          <TempChart data={data} />
          <table style={{ width: '100%', marginTop: 16 }}>
            <thead><tr><th>Date</th><th>FCE</th><th>FCR</th><th>Feed (kg)</th><th>Gain (kg)</th></tr></thead>
            <tbody>
              {data.slice(-14).map((r)=> (
                <tr key={r.date}><td>{r.date}</td><td>{r.fce}</td><td>{r.fcr}</td><td>{r.feed_given_kg}</td><td>{r.biomass_gain_kg}</td></tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  )
}

export default function App(){
  return (
    <AuthProvider>
      <Dashboard />
    </AuthProvider>
  )
}
```

---

# Quickstart

1. **Local with Docker**

```
cp .env.example .env
make compose-up
# in another terminal, seed the DB (requires host Python) or exec into api to run seed
make seed
# open http://localhost:5173 (dev) or http://localhost:4173 (preview)
# API docs: http://localhost:8000/docs
```

2. **Local without Docker**

```
# start Mongo locally (or leave docker-compose mongo running)
make api   # starts FastAPI on :8000
make web   # starts React on :5173
make seed  # loads data into Mongo
```

> Auth is **disabled by default** (`AUTH_DISABLED=true`). Once you create Auth0 apps, set `AUTH_DISABLED=false` and the Auth0 vars in `.env`, then restart API and frontend.

---

# Notes

* The ETL uses Open‑Meteo; if network is blocked, set `avg_temperature_C` later or re‑run seed.
* For Cosmos DB, update `MONGO_URI` to your Cosmos Mongo connection string and re‑run `make seed`.
* Keep free tiers on Azure; add teardown notes in README when you deploy.
