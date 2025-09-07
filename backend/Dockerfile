# ---- build runtime ----
FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir uv && python - <<'PY'
import tomllib, subprocess
deps = tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']
subprocess.run(['uv', 'pip', 'install', '--system', *deps], check=True)
PY
COPY app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

