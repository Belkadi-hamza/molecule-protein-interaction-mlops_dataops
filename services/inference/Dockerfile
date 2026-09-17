FROM python:3.11-slim
WORKDIR /app
COPY services/inference /app/services/inference
RUN pip install --no-cache-dir /app/services/inference
ENV MODEL_PATH=/data/model.joblib
VOLUME ["/data"]
EXPOSE 8000
CMD ["uvicorn", "inference.main:app", "--host", "0.0.0.0", "--port", "8000"]