# Molecule-Protein Interaction MLOps

This project loads molecule-protein interaction CSV data into DuckDB, trains a
scikit-learn classifier through Dagster, records parameters, metrics, and the
model in MLflow, and serves inference through FastAPI.

The implementation is split into services:

- `services/ingestion`: CSV upload and DuckDB raw-table loading.
- `services/feature-engineering`: creates the DuckDB training feature table.
- `services/validation`: checks columns, rows, and target classes.
- `services/training`: trains and publishes the MLflow/joblib model.
- `services/inference`: serves predictions from the published model.

Dagster connects them in one workflow: `ingest -> engineer_features -> validate
-> train`. The root API triggers this workflow after a CSV upload. Services
share the DuckDB/model volume when deployed as separate containers.

The shared data contract is the header in `shared/cobweb_bdb.csv`:
`target_name`, `inhibitor_name`, `monomer_id`, `affinity_type`,
`affinity_value`, `affinity_value_display`, `affinity_strength`,
`reactant_set_id`, and `source_organism`.

## Getting started

### Installing dependencies

**Option 1: uv**

Ensure [`uv`](https://docs.astral.sh/uv/) is installed following their [official documentation](https://docs.astral.sh/uv/getting-started/installation/).

Create a virtual environment, and install the required dependencies using _sync_:

```bash
uv sync
```

Then, activate the virtual environment:

| OS | Command |
| --- | --- |
| MacOS | ```source .venv/bin/activate``` |
| Windows | ```.venv\Scripts\activate``` |

**Option 2: pip**

Install the python dependencies with [pip](https://pypi.org/project/pip/):

```bash
python3 -m venv .venv
```

Then activate the virtual environment:

| OS | Command |
| --- | --- |
| MacOS | ```source .venv/bin/activate``` |
| Windows | ```.venv\Scripts\activate``` |

Install the required dependencies:

```bash
pip install -e ".[dev]"
```

### Run the pipeline directly

The repository CSV can be loaded and trained locally with:

```bash
PYTHONPATH=src uv run python -c \
	"from my_project.pipeline import training_job; print(training_job.execute_in_process().success)"
```

This creates `data/warehouse.duckdb`, `data/model.joblib`, and the SQLite
MLflow store at `data/mlflow.db`. Dagster logs every op and the training run
logs metrics and the model artifact to MLflow.

### Running Dagster

Start the Dagster UI web server:

```bash
uv run dg dev
```

Open http://localhost:3000 in your browser to see the project.

### Run everything with Docker Compose

Docker Compose starts the upload/orchestration API, Dagster UI, MLflow, and the
standalone inference service. DuckDB and the published model are shared through
a persistent volume.

```bash
docker compose up --build
```

Endpoints:

- API and upload workflow: http://localhost:8000
- Dagster UI: http://localhost:3000
- MLflow UI: http://localhost:5000
- Standalone inference: http://localhost:8001/predict

Upload data after the services are healthy:

```bash
curl -F "file=@shared/cobweb_bdb.csv" http://localhost:8000/data/upload
```

Stop the stack while preserving data volumes:

```bash
docker compose down
```

Remove generated databases and model artifacts too:

```bash
docker compose down -v
```

### Run the APIs

Start the data and inference API:

```bash
PYTHONPATH=src uv run uvicorn my_project.api:app --reload --port 8000
```

The root API exposes `/data/upload` to trigger the complete Dagster workflow and
`/inference/predict` as a convenience gateway. The independently deployable
inference service exposes the same contract at `/predict`:

```bash
docker build -f services/inference/Dockerfile .
docker run --rm -p 8000:8000 -v "$PWD/data:/data" molecule-inference
```

Upload a CSV to run the Dagster workflow:

```bash
curl -F "file=@shared/cobweb_bdb.csv" http://localhost:8000/data/upload
```

After a model exists, call inference with the eight non-target shared columns:

```bash
curl -X POST http://localhost:8000/inference/predict \
	-H 'Content-Type: application/json' \
	-d '{"target_name":"protein","inhibitor_name":"BDBM1","monomer_id":1,"affinity_type":"IC50","affinity_value":10.0,"affinity_value_display":"10","reactant_set_id":1,"source_organism":"Human"}'
```

Useful environment variables are `DUCKDB_PATH`, `MODEL_PATH`,
`MLFLOW_TRACKING_URI`, and `MLFLOW_EXPERIMENT`.

Each service can also be built from the repository root with its Dockerfile;
the ingestion, feature-engineering, validation, and training services use the
same `/data` volume so Dagster-orchestrated steps see the same warehouse and
model artifacts.

## Learn more

To learn more about this template and Dagster in general:

- [Dagster Documentation](https://docs.dagster.io/)
- [Dagster University](https://courses.dagster.io/)
- [Dagster Slack Community](https://dagster.io/slack)
