from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from dagster import DagsterInstance
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
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


def run_training_pipeline(source_path: str) -> None:
  result = training_job.execute_in_process(
    run_config={
      "ops": {
        name: {"config": {"source_path": source_path}}
        for name in ("ingest", "engineer_features", "validate", "train")
      }
    },
    instance=DagsterInstance.ephemeral(),
  )
  if not result.success:
    raise RuntimeError("Dagster training run failed")


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Molecule Interaction API</title>
<style>
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body {
    font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    max-width: 860px; margin: 2rem auto; padding: 0 1rem; line-height: 1.5;
  }
  h1 { margin-bottom: 0.25rem; }
  .sub { color: #666; margin-top: 0; }
  section {
    border: 1px solid #ddd; border-radius: 10px;
    padding: 1.25rem 1.5rem; margin: 1.5rem 0;
  }
  h2 { margin-top: 0; }
  label { display: block; font-weight: 600; margin: 0.6rem 0 0.2rem; font-size: 0.9rem; }
  input, select {
    width: 100%; padding: 0.5rem; border: 1px solid #bbb;
    border-radius: 6px; font-size: 0.95rem;
  }
  button {
    margin-top: 1rem; padding: 0.6rem 1.2rem; border: none;
    border-radius: 6px; background: #2563eb; color: white;
    font-size: 1rem; cursor: pointer;
  }
  button:disabled { background: #94a3b8; cursor: not-allowed; }
  button:hover:not(:disabled) { background: #1d4ed8; }
  pre {
    background: #0f172a; color: #e2e8f0; padding: 1rem;
    border-radius: 8px; overflow-x: auto; font-size: 0.85rem;
  }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 1rem; }
  @media (max-width: 640px) { .grid { grid-template-columns: 1fr; } }
  .status { font-weight: 600; }
  .ok { color: #16a34a; }
  .err { color: #dc2626; }
</style>
</head>
<body>
  <h1>Molecule Interaction API</h1>
  <p class="sub">Upload training data or run an inference prediction.</p>

  <section>
    <h2>1. Upload training data (CSV)</h2>
    <p>Uploading a CSV queues the Dagster <code>training_job</code> pipeline in the background.</p>
    <form id="upload-form">
      <label for="file">CSV file</label>
      <input type="file" id="file" name="file" accept=".csv" required />
      <button type="submit">Upload &amp; Queue Training</button>
    </form>
    <p id="upload-status" class="status"></p>
    <pre id="upload-output" hidden></pre>
  </section>

  <section>
    <h2>2. Inference prediction</h2>
    <form id="predict-form">
      <div class="grid">
        <div>
          <label for="target_name">Target name</label>
          <input id="target_name" name="target_name" value="EGFR" required />
        </div>
        <div>
          <label for="inhibitor_name">Inhibitor name</label>
          <input id="inhibitor_name" name="inhibitor_name" value="Gefitinib" required />
        </div>
        <div>
          <label for="monomer_id">Monomer ID</label>
          <input id="monomer_id" name="monomer_id" type="number" value="1" required />
        </div>
        <div>
          <label for="affinity_type">Affinity type</label>
          <select id="affinity_type" name="affinity_type">
            <option>IC50</option>
            <option>Ki</option>
            <option>Kd</option>
            <option>EC50</option>
          </select>
        </div>
        <div>
          <label for="affinity_value">Affinity value (numeric)</label>
          <input id="affinity_value" name="affinity_value" type="number" step="any" value="10.5" required />
        </div>
        <div>
          <label for="affinity_value_display">Affinity value (display)</label>
          <input id="affinity_value_display" name="affinity_value_display" value="10.5 nM" required />
        </div>
        <div>
          <label for="reactant_set_id">Reactant set ID</label>
          <input id="reactant_set_id" name="reactant_set_id" type="number" value="1" required />
        </div>
        <div>
          <label for="source_organism">Source organism</label>
          <input id="source_organism" name="source_organism" value="Homo sapiens" required />
        </div>
      </div>
      <button type="submit">Predict</button>
    </form>
    <p id="predict-status" class="status"></p>
    <pre id="predict-output" hidden></pre>
  </section>

<script>
  const API_BASE = window.location.origin;

  // --- Upload form ---
  document.getElementById("upload-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById("file");
    const statusEl = document.getElementById("upload-status");
    const outputEl = document.getElementById("upload-output");
    const button = e.target.querySelector("button");

    if (!fileInput.files.length) return;
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    button.disabled = true;
    statusEl.textContent = "Uploading and queueing training job...";
    statusEl.className = "status";
    outputEl.hidden = true;

    try {
      const res = await fetch(`${API_BASE}/data/upload`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        statusEl.textContent = "Upload accepted. Training is running in the background.";
        statusEl.className = "status ok";
      } else {
        statusEl.textContent = `Error: ${data.detail || res.statusText}`;
        statusEl.className = "status err";
      }
      outputEl.textContent = JSON.stringify(data, null, 2);
      outputEl.hidden = false;
    } catch (err) {
      statusEl.textContent = `Network error: ${err.message}`;
      statusEl.className = "status err";
    } finally {
      button.disabled = false;
    }
  });

  // --- Predict form ---
  document.getElementById("predict-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const statusEl = document.getElementById("predict-status");
    const outputEl = document.getElementById("predict-output");
    const button = form.querySelector("button");

    const payload = {
      target_name: form.target_name.value,
      inhibitor_name: form.inhibitor_name.value,
      monomer_id: parseInt(form.monomer_id.value, 10),
      affinity_type: form.affinity_type.value,
      affinity_value: parseFloat(form.affinity_value.value),
      affinity_value_display: form.affinity_value_display.value,
      reactant_set_id: parseInt(form.reactant_set_id.value, 10),
      source_organism: form.source_organism.value,
    };

    button.disabled = true;
    statusEl.textContent = "Predicting...";
    statusEl.className = "status";
    outputEl.hidden = true;

    try {
      const res = await fetch(`${API_BASE}/inference/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (res.ok) {
        statusEl.textContent =
          `Predicted affinity strength: ${data.affinity_strength} ` +
          `(probability ${(data.probability * 100).toFixed(1)}%)`;
        statusEl.className = "status ok";
      } else {
        statusEl.textContent = `Error: ${data.detail || res.statusText}`;
        statusEl.className = "status err";
      }
      outputEl.textContent = JSON.stringify(data, null, 2);
      outputEl.hidden = false;
    } catch (err) {
      statusEl.textContent = `Network error: ${err.message}`;
      statusEl.className = "status err";
    } finally {
      button.disabled = false;
    }
  });
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index() -> HTMLResponse:
    return HTMLResponse(content=INDEX_HTML)


# ---------------------------------------------------------------------------
# Existing endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/data/upload", status_code=202)
async def upload_data(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> dict:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")
    upload_dir = Path(tempfile.gettempdir()) / "molecule-interaction-uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / Path(file.filename).name
    with destination.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    await file.close()
    background_tasks.add_task(run_training_pipeline, str(destination))
    return {
        "status": "queued",
        "dataset": file.filename,
        "message": "Training has been queued and will continue in the background.",
    }


@app.post("/inference/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest) -> PredictionResponse:
    try:
        label, probability = predict_model(request.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return PredictionResponse(affinity_strength=label, probability=probability)