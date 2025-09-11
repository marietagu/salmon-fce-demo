# ---- Makefile: quick dev commands ----
.PHONY: help dev api web seed compose-up compose-down lint test fmt

help:
	@echo "Targets:\n\
	dev           - run backend (uvicorn) and frontend (vite) locally\n\
	api           - run FastAPI locally\n\
	web           - run React dev server\n\
	seed          - generate + load 365d into Mongo (local)\n\
	compose-up    - docker compose up --build\n\
	compose-down  - docker compose down -v\n\
	lint          - ruff lint (backend)\n\
	fmt           - black format (backend)\n\
	test          - pytest (backend)\n"

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
	cd etl && (uv run --with httpx --with motor python seed.py || (python -m pip install -U pip && python -m pip install httpx motor && python seed.py))

# One-shot top-up to fill missing days up to today
seed-topup:
	cd etl && (uv run --with httpx --with motor python top_up.py || (python -m pip install -U pip && python -m pip install httpx motor && python top_up.py))

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

