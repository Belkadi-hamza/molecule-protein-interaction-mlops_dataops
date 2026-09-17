from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from dagster import DagsterInstance
from fastapi import FastAPI, File, HTTPException, UploadFile
from inference.predictor import predict as predict_model
from pydantic import BaseModel, Field

from my_project.pipeline import training_job

app = FastAPI(title="Molecule Interaction API", version="0.1.0")


class PredictionRequest(BaseModel):
    target_name: str
    inhibitor_name: str
    monomer_id: int
    affinity_type: str
    affinity_value: float
    affinity_value_display: str
    reactant_set_id: int
    source_organism: str


class PredictionResponse(BaseModel):
    affinity_strength: int
    probability: float = Field(ge=0, le=1)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/data/upload")
async def upload_data(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")
    upload_dir = Path(tempfile.gettempdir()) / "molecule-interaction-uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / Path(file.filename).name
    with destination.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    result = training_job.execute_in_process(
        run_config={"ops": {
            name: {"config": {"source_path": str(destination)}}
            for name in ("ingest", "engineer_features", "validate", "train")
        }},
        instance=DagsterInstance.ephemeral(),
    )
    if not result.success:
        raise HTTPException(status_code=500, detail="Dagster training run failed")
    return {"status": "completed", "run_id": result.run_id, "dataset": file.filename}


@app.post("/inference/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest) -> PredictionResponse:
    try:
        label, probability = predict_model(request.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return PredictionResponse(affinity_strength=label, probability=probability)