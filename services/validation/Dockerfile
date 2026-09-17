FROM python:3.11-slim
WORKDIR /app
COPY shared/data-contract /app/shared/data-contract
COPY services/validation /app/services/validation
RUN pip install --no-cache-dir /app/shared/data-contract /app/services/validation
ENV DUCKDB_PATH=/data/warehouse.duckdb
RUN mkdir -p /data
CMD ["python", "-c", "from validation import validate_features; validate_features()"]