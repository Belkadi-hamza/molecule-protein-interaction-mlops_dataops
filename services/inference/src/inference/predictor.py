import os
from pathlib import Path

import joblib

MODEL_PATH = Path(os.getenv("MODEL_PATH", "data/model.joblib"))


def predict(features: dict) -> tuple[int, float]:
    if not MODEL_PATH.exists():
        raise FileNotFoundError("No trained model is available")
    model = joblib.load(MODEL_PATH)
    probabilities = model.predict_proba([features])[0]
    index = int(probabilities.argmax())
    return int(model.classes_[index]), float(probabilities[index])