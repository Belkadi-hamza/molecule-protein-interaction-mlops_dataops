"""
Ingestion API
-------------
A small FastAPI service that receives CSV file uploads over HTTP and
loads them into a DuckDB database file. Designed to run in its own
container and be triggered/orchestrated later by Dagster (via an op
that calls this API, or via a Dagster-managed container run).
"""

import logging
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import duckdb
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingestion")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Path to the DuckDB file. Mount a volume here so the data survives
# container restarts and can be shared with Dagster / other services.
DUCKDB_PATH = os.environ.get("DUCKDB_PATH", "/data/warehouse.duckdb")

# Only allow simple, safe table names (letters, numbers, underscore).
TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

app = FastAPI(title="Ingestion API", version="0.1.0")


def get_connection() -> duckdb.DuckDBPyConnection:
    Path(DUCKDB_PATH).parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(DUCKDB_PATH)


class IngestResponse(BaseModel):
    table: str
    rows_loaded: int
    columns: list[str]
    mode: str


class TableInfo(BaseModel):
    table: str
    row_count: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
def health():
    """Basic liveness/readiness check (useful for Docker/Dagster health checks)."""
    try:
        con = get_connection()
        con.execute("SELECT 1").fetchone()
        con.close()
        return {"status": "ok", "duckdb_path": DUCKDB_PATH}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"DuckDB unavailable: {exc}") from exc


@app.post("/ingest", response_model=IngestResponse)
async def ingest_csv(
    file: UploadFile = File(...),
    table_name: Optional[str] = Query(
        None,
        description="Target table name. Defaults to the CSV filename (without extension).",
    ),
    mode: str = Query(
        "replace",
        pattern="^(replace|append|fail)$",
        description="What to do if the table already exists: replace, append, or fail.",
    ),
):
    """
    Upload a CSV file and load it into a DuckDB table.

    - **replace**: drop and recreate the table from this file
    - **append**: insert the new rows into the existing table (schema must match)
    - **fail**: error out if the table already exists
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")

    resolved_table = table_name or Path(file.filename).stem
    if not TABLE_NAME_RE.match(resolved_table):
        raise HTTPException(
            status_code=400,
            detail="table_name must start with a letter/underscore and contain only "
            "letters, numbers, and underscores",
        )

    # Stream the upload to a temp file so we don't hold huge files in memory,
    # and so DuckDB's fast CSV reader (read_csv_auto) can read straight off disk.
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp_path = tmp.name
            shutil.copyfileobj(file.file, tmp)
        await file.close()

        con = get_connection()
        try:
            table_exists = con.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_name = ?",
                [resolved_table],
            ).fetchone()[0] > 0

            if table_exists and mode == "fail":
                raise HTTPException(
                    status_code=409, detail=f"Table '{resolved_table}' already exists"
                )

            if not table_exists or mode == "replace":
                con.execute(
                    f'CREATE OR REPLACE TABLE "{resolved_table}" AS '
                    f"SELECT * FROM read_csv_auto(?, header=true)",
                    [tmp_path],
                )
            else:  # append
                con.execute(
                    f'INSERT INTO "{resolved_table}" '
                    f"SELECT * FROM read_csv_auto(?, header=true)",
                    [tmp_path],
                )

            row_count, = con.execute(
                f'SELECT count(*) FROM "{resolved_table}"'
            ).fetchone()
            columns = [
                row[0]
                for row in con.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = ? ORDER BY ordinal_position",
                    [resolved_table],
                ).fetchall()
            ]
        finally:
            con.close()

        logger.info("Loaded %s rows into table '%s' (mode=%s)", row_count, resolved_table, mode)
        return IngestResponse(
            table=resolved_table, rows_loaded=row_count, columns=columns, mode=mode
        )

    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to ingest CSV")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.get("/tables", response_model=list[TableInfo])
def list_tables():
    """List tables currently in the DuckDB file, with row counts."""
    con = get_connection()
    try:
        names = [
            row[0]
            for row in con.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main'"
            ).fetchall()
        ]
        result = []
        for name in names:
            count = con.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
            result.append(TableInfo(table=name, row_count=count))
        return result
    finally:
        con.close()


@app.delete("/tables/{table_name}")
def drop_table(table_name: str):
    if not TABLE_NAME_RE.match(table_name):
        raise HTTPException(status_code=400, detail="Invalid table name")
    con = get_connection()
    try:
        con.execute(f'DROP TABLE IF EXISTS "{table_name}"')
        return {"dropped": table_name}
    finally:
        con.close()
