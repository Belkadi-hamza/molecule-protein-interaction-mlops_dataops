FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY services ./services
COPY shared ./shared

RUN pip install --no-cache-dir \
    "dagster==1.13.23" \
    "dagster-webserver>=1.13.23,<1.14" \
    ./shared/data-contract \
    ./services/ingestion \
    ./services/feature-engineering \
    ./services/validation \
    ./services/training \
    ./services/inference \
    && pip install --no-cache-dir --no-deps .

ENV PYTHONPATH=/app/src
ENV DUCKDB_PATH=/app/data/warehouse.duckdb
ENV MODEL_PATH=/app/data/model.joblib
ENV MLFLOW_TRACKING_URI=http://mlflow:5000
ENV MLFLOW_EXPERIMENT=molecule-protein-interaction

RUN mkdir -p /app/data

EXPOSE 8000 3000

CMD ["uvicorn", "my_project.api:app", "--host", "0.0.0.0", "--port", "8000"]