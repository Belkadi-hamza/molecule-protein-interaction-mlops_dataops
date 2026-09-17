FROM python:3.11-slim
WORKDIR /app
COPY shared/data-contract /app/shared/data-contract
COPY services/training /app/services/training
RUN pip install --no-cache-dir /app/shared/data-contract /app/services/training
ENV DUCKDB_PATH=/data/warehouse.duckdb
ENV MODEL_PATH=/data/model.joblib
ENV MLFLOW_TRACKING_URI=sqlite:////data/mlflow.db
RUN mkdir -p /data
CMD ["python", "-c", "from training import train_model; train_model()"]