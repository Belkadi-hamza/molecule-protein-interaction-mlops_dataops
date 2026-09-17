FROM python:3.11-slim

WORKDIR /app

# System deps kept minimal; duckdb ships pre-built wheels so no compiler needed.
COPY shared/data-contract /app/shared/data-contract
COPY services/ingestion /app/services/ingestion

RUN pip install --no-cache-dir /app/shared/data-contract /app/services/ingestion

# DuckDB file lives here; mount a volume at /data to persist it
# and to let other services (e.g. a Dagster asset) read the same file.
ENV DUCKDB_PATH=/data/warehouse.duckdb
RUN mkdir -p /data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "ingestion.main:app", "--host", "0.0.0.0", "--port", "8000"]
