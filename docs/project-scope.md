# Vision (crisp)

Deliver a lean, end‑to‑end salmon Feed Conversion Efficiency (FCE) monitoring demo that proves practical data‑engineering skills: ingest → store → serve → visualise, deployed on Azure, secured with JWT, documented and reproducible. The system communicates environmental stewardship (kaitiakitanga) by surfacing FCE alongside temperature context and transparent data provenance (synthetic + public weather).

---

# Final Tech Stack (single, consolidated)

**Language & Tooling**

* Python **3.11** (runtime for ETL + API)
* Node **20** (frontend)
* **uv** (or Poetry) for Python dependency management; choose **uv** for speed
* **Docker** for containers; **docker-compose** for local orchestration

**Data & Ingestion**

* Synthetic generator: Python (`numpy`, `pandas`, `pydantic`)
* Weather: **Open‑Meteo** Daily API (no key, free) via `httpx`
* Validation: `pydantic` models

**Database**

* **MongoDB 7** locally (Docker)
* **Azure Cosmos DB (Mongo API)** in cloud
* Async client: **motor**
* Collection: `salmon_fce.fce_daily`

**Backend API**

* **FastAPI** + **Uvicorn**
* JWT verification: `python-jose`, JWKS fetch via `httpx`, in‑memory cache
* Logging: `structlog` (JSON logs)

**Auth**

* **Auth0** (one **API** + one **SPA** app)
* RS256 JWTs validated by JWKS; audience/issuer enforced

**Frontend**

* **React + Vite**
* Charts: **Recharts** (line charts, lightweight)
* Auth: **@auth0/auth0-react**
* Data fetching: **TanStack Query** (loading/error states & caching)
* Styling: **Tailwind CSS**

**Azure Deployment**

* API: **Azure Container Apps** (or App Service Docker if preferred)
* Frontend: **Azure Static Web Apps**
* Database: **Cosmos DB (Mongo API)** Free/low tier
* Registry: **Azure Container Registry (ACR)** (or GHCR)
* Monitoring: Container logs + ACA diagnostics

**Test & Quality**

* Unit/smoke tests with **pytest** and **httpx** test client
* Linting/format: **ruff** + **black**

---

# Repository Layout (final)

```
root/
  etl/                # synthetic data + weather fetch + loader
  backend/            # FastAPI app (JWT‑protected)
  frontend/           # React SPA (Auth0, Recharts)
  infra/              # docker-compose, Azure notes/scripts
  .env.example
  README.md
  Makefile            # quick commands for dev
```

---

# Environment Variables (authoritative list)

**Backend**

* `MONGO_URI` (e.g., mongodb://mongo:27017 or Cosmos Mongo URI)
* `MONGO_DB=salmon_fce`
* `MONGO_COLL=fce_daily`
* `AUTH0_DOMAIN=` (e.g., your-tenant.eu.auth0.com)
* `AUTH0_AUDIENCE=` (identifier of your Auth0 API)
* `ALLOWED_ORIGINS=` (comma‑sep for local + prod frontend)

**ETL**

* `OPEN_METEO_LAT=` `OPEN_METEO_LON=`
* `SEED_START=YYYY-MM-DD` `SEED_DAYS=365`
* `SITE_NAME=` (e.g., Marlborough Sounds)

**Frontend**

* `VITE_API_BASE_URL=`
* `VITE_AUTH0_DOMAIN=` `VITE_AUTH0_CLIENT_ID=` `VITE_AUTH0_AUDIENCE=`

---

# Data Model (clarified)

**Collection:** `salmon_fce.fce_daily` (indexes: `{ date: 1, site: 1 }`)
**Document per day:**

```json
{
  "date": "YYYY-MM-DD",
  "site": "Marlborough Sounds",
  "feed_given_kg": 0.0,
  "biomass_gain_kg": 0.0,
  "fcr": 0.0,               // feed_given_kg / biomass_gain_kg
  "fce": 0.0,               // 1 / fcr
  "health_score": 0.0,      // 0–100 synthetic heuristic
  "avg_temperature_C": 0.0,  // Open‑Meteo daily mean
  "regime": "normal" | "reduced"
}
```

**Integrity rules:** non‑null `date`, no duplicates `{date, site}`, non‑negative `feed_given_kg` and `biomass_gain_kg`, `fce == 1/fcr` within tolerance.

---

# API Contract (final MVP)

* `GET /healthz` → `{ status: "ok" }` (public)
* `GET /api/metrics?start=YYYY-MM-DD&end=YYYY-MM-DD&site=Marlborough%20Sounds`
  Returns `[DailyRecord]`, JWT required, max 1000 docs per call (server‑side cap)
* `GET /api/metrics/latest?site=` → latest day doc
* `GET /api/summary?start=&end=&site=` → `{ avg_fcr, avg_fce, count, start, end, site }`
  **Auth**: `/api/*` requires `Authorization: Bearer <JWT>`; issuer/audience verified via JWKS; CORS locked to frontend.

---

# Architecture (concise)

* **ETL**: generator (synthetic cohort, regime windows) + weather fetch → merge/clean → bulk upsert to Mongo
* **Store**: Mongo/Cosmos with `{date, site}` index
* **Serve**: FastAPI (async motor), JWT guard, OpenAPI docs
* **Visualise**: React SPA (Auth0, TanStack Query, Recharts)
* **Run**: Docker Compose locally; Azure (ACA + SWA + Cosmos) in cloud

---

# Ordered Implementation Plan (epics → tasks)

## EPIC 0 — Bootstrap (0.25 day)

1. Create repo layout; init Git; add `.env.example`, Makefile with `dev`, `seed`, `api`, `web`, `compose-up` targets.
2. Pin versions (Python 3.11, Node 20); set up `uv` and `package.json`.

## EPIC 1 — Data Ingestion & Seeding (0.75 day)

3. Implement `etl/generate_synthetic.py` (params: `start_date`, `days`, `site`, `seed`).
4. Implement `etl/fetch_weather.py` (Open‑Meteo daily mean temp).
5. Implement `etl/merge_and_load.py` (compute FCR/FCE; validate; bulk upsert; create indexes).
6. `make seed` to generate 365 days and load local Mongo.

## EPIC 2 — Backend API (0.75 day)

7. Scaffold FastAPI app (`backend/app/main.py`) with lifespan motor client; Pydantic responses.
8. Implement routes: `/healthz`, `/api/metrics`, `/api/metrics/latest`, `/api/summary`.
9. Add pagination/safeguards, parameter validation, and CORS (local + prod origin).

## EPIC 3 — Frontend (0.75 day)

10. Vite + React scaffold; Tailwind; TanStack Query.
11. Pages: single dashboard with date range presets (30/90/180/365), site select.
12. Charts: FCE vs Date; Temperature vs Date (separate chart).
13. Empty/loading/error states + small table (last 14 days).

## EPIC 4 — Authentication (0.75 day)

14. Auth0: create API & SPA, configure callback/logout URLs and CORS.
15. Backend: add JWT dependency (JWKS caching, audience/issuer check) and secure `/api/*`.
16. Frontend: integrate `@auth0/auth0-react`; login/logout; attach token to fetches.
17. Verify 401 → 200 flow (Swagger authorize + SPA test).

## EPIC 5 — Containers & Local Orchestration (0.5 day)

18. Dockerize backend (multi‑stage, non‑root).
19. Optional: containerize frontend (nginx) or run dev server locally.
20. `docker-compose.yml`: `mongo`, `backend`, `frontend` (if containerized). Healthchecks included.

## EPIC 6 — Azure Deployment (0.75–1 day)

21. Provision RG, ACR, Cosmos (Mongo API), Container Apps (or App Service), Static Web Apps.
22. Configure API env vars and CORS; push image to ACR; deploy backend; deploy SPA.
23. Re‑run `make seed` against Cosmos URI.
24. Smoke tests: `/healthz`, then SPA → login → charts render.

## EPIC 7 — QA, Docs & Polish (0.5 day)

25. Validate metric ranges (FCR \~0.8–2.0; FCE inverse), visible regime effect, axes/labels.
26. README: overview, quickstart, env table, curl examples, architecture diagram, teardown notes.
27. Demo script; optional GIF. Tag release `v1.0`.

**Stretch**

* GitHub Actions CI (lint/test/build/push) + ACA deploy.
* Azure Key Vault for secrets.
* Extra charts (scatter: feed vs gain; cumulative lines).
* `/api/insights` (corr FCE↔temp; simple anomaly flag).

---

# Acceptance Criteria (Definition of Done)

* Public **API URL** (ACA) with Swagger and JWT‑protected `/api/*`.
* Public **Dashboard URL** (SWA) showing charts for selected range/site.
* **365+ days** of data in Cosmos; `{date, site}` index present.
* **Reproducible**: `make seed`, `docker-compose up`, and deploy notes work as documented.
* **Logs visible** in ACA; 401 unauthenticated; 200 authenticated.

---

# Risk Register (with mitigations)

* **Auth/CORS misconfig** → Test locally with Swagger `Authorize`; restrict CORS last, not first.
* **Cosmos cost/limits** → Free/low tier; cap RU/s; teardown instructions.
* **Weather gaps** → Cache responses; fallback to synthetic sinusoid.
* **Time pressure** → Keep UI minimal; if needed, ship one chart and `/summary` endpoint first.

---

# Roadmap by Day (7‑day plan)

* **Day 1**: EPIC 0 + start EPIC 1; seed local DB.
* **Day 2**: Finish EPIC 1 + EPIC 2 (API without auth).
* **Day 3**: EPIC 3 (frontend basic charts).
* **Day 4**: Polish filters + stability.
* **Day 5**: EPIC 4 (Auth0 end‑to‑end).
* **Day 6**: EPIC 5–6 (containers + Azure deploy + seed Cosmos).
* **Day 7**: EPIC 7 (QA, docs, demo script, teardown notes).

---

# Demo Narrative (2–3 min)

1. Login via Auth0 → 2) Dashboard shows FCE + Temperature → 3) Toggle date presets to reveal regime effect → 4) Open Swagger and call `/api/summary` → 5) Show Azure resource group + ACA logs.

---

# Stewardship & Māori Engagement (in the demo)

* Clear labelling that data are **synthetic + public weather**; document generation logic and limitations.
* Focus on **environmental outcomes** (efficient feed use, reduced waste).
* Use plain language in README; avoid overstating model fidelity; invite collaborative extension.
