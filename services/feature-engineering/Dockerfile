FROM python:3.11-slim
WORKDIR /app
COPY shared/data-contract /app/shared/data-contract
COPY services/feature-engineering /app/services/feature-engineering
RUN pip install --no-cache-dir /app/shared/data-contract /app/services/feature-engineering
ENV DUCKDB_PATH=/data/warehouse.duckdb
RUN mkdir -p /data
CMD ["python", "-c", "from feature_engineering import build_features; build_features()"]