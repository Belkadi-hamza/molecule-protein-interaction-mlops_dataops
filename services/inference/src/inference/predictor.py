import os
from pathlib import Path

import joblib
import pandas as pd

MODEL_PATH = Path(os.getenv("MODEL_PATH", "data/model.joblib"))


def predict(features: dict) -> tuple[int, float]:
    if not MODEL_PATH.exists():
        raise FileNotFoundError("No trained model is available")
    model = joblib.load(MODEL_PATH)
    frame = pd.DataFrame([features])
    probabilities = model.predict_proba(frame)[0]
    index = int(probabilities.argmax())
    return int(model.classes_[index]), float(probabilities[index])