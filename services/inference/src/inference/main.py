from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from inference.predictor import predict

app = FastAPI(title="Molecule Interaction Inference", version="0.1.0")


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


@app.post("/predict", response_model=PredictionResponse)
def predict_interaction(request: PredictionRequest) -> PredictionResponse:
    try:
        label, probability = predict(request.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return PredictionResponse(affinity_strength=label, probability=probability)