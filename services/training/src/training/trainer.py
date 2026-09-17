import os
from pathlib import Path

import duckdb
import joblib
import mlflow
import mlflow.sklearn
from data_contract import CATEGORICAL_COLUMNS, FEATURE_TABLE, NUMERIC_COLUMNS, TARGET_COLUMN
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

MODEL_PATH = Path(os.getenv("MODEL_PATH", "data/model.joblib"))
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///data/mlflow.db")
MLFLOW_EXPERIMENT = os.getenv("MLFLOW_EXPERIMENT", "molecule-protein-interaction")


def train_model(
    database_path: str = "/data/warehouse.duckdb",
    table_name: str = FEATURE_TABLE,
) -> dict:
    connection = duckdb.connect(database_path)
    try:
        frame = connection.execute(f'SELECT * FROM "{table_name}"').df()
    finally:
        connection.close()
    frame = frame.dropna(subset=[TARGET_COLUMN]).copy()
    features = frame.drop(columns=[TARGET_COLUMN])
    target = frame[TARGET_COLUMN].astype(int)
    features = features.drop(columns=["affinity_log_value"], errors="ignore")
    transformer = ColumnTransformer([
        ("categorical", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLUMNS),
        ("numeric", StandardScaler(), NUMERIC_COLUMNS),
    ])
    model = Pipeline([
        ("features", transformer),
        ("classifier", LogisticRegression(max_iter=500, class_weight="balanced")),
    ])
    x_train, x_test, y_train, y_test = train_test_split(
        features, target, test_size=max(0.2, 2 / len(frame)),
        random_state=42, stratify=target
    )
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT)
    with mlflow.start_run() as run:
        model.fit(x_train, y_train)
        predictions = model.predict(x_test)
        probabilities = model.predict_proba(x_test)
        metrics = {
            "accuracy": float(accuracy_score(y_test, predictions)),
            "f1_weighted": float(f1_score(y_test, predictions, average="weighted", zero_division=0)),
        }
        if len(model.classes_) == 2:
            metrics["roc_auc"] = float(roc_auc_score(y_test, probabilities[:, 1]))
        mlflow.log_params({"rows": len(frame), "classes": len(model.classes_)})
        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(model, "model")
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, MODEL_PATH)
        return {**metrics, "run_id": run.info.run_id, "rows": len(frame)}