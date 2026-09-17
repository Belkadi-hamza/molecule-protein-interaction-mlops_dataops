from dagster import Config, OpExecutionContext, job, op
from feature_engineering import build_features
from ingestion.loader import load_csv
from training import train_model
from validation import validate_features


class PipelineConfig(Config):
    source_path: str = "shared/cobweb_bdb.csv"
    database_path: str = "data/warehouse.duckdb"


@op
def ingest(context: OpExecutionContext, config: PipelineConfig) -> int:
    rows = load_csv(config.source_path, config.database_path)
    context.log.info("Ingestion service loaded %s rows into DuckDB", rows)
    return rows


@op
def engineer_features(context: OpExecutionContext, config: PipelineConfig, _rows: int) -> int:
    rows = build_features(config.database_path)
    context.log.info("Feature engineering service created %s rows", rows)
    return rows


@op
def validate(context: OpExecutionContext, config: PipelineConfig, _feature_rows: int) -> int:
    rows = validate_features(config.database_path)
    context.log.info("Validation service accepted %s rows", rows)
    return rows


@op
def train(context: OpExecutionContext, config: PipelineConfig, _validated_rows: int) -> dict:
    metrics = train_model(config.database_path)
    context.log.info("Training service published model: %s", metrics)
    return metrics


@job
def training_job():
    rows = ingest()
    features = engineer_features(rows)
    validated = validate(features)
    train(validated)