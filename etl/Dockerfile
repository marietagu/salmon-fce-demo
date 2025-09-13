FROM python:3.11-slim
WORKDIR /app
COPY . /app/
RUN pip install --no-cache-dir motor httpx
CMD ["python", "-u", "top_up.py"]


