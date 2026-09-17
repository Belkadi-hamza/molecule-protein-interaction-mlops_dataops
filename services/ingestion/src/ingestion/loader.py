from pathlib import Path

import duckdb

from data_contract import RAW_TABLE, SHARED_COLUMNS


def load_csv(
    source_path: str,
    database_path: str = "/data/warehouse.duckdb",
    table_name: str = RAW_TABLE,
) -> int:
    source = Path(source_path)
    if not source.exists() or source.suffix.lower() != ".csv":
        raise ValueError(f"CSV file does not exist: {source}")
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(database_path)
    try:
        columns = [row[0] for row in connection.execute(
            "DESCRIBE SELECT * FROM read_csv_auto(?, header=true)", [str(source)]
        ).fetchall()]
        missing = sorted(set(SHARED_COLUMNS) - set(columns))
        if missing:
            raise ValueError(f"CSV is missing shared columns: {', '.join(missing)}")
        connection.execute(
            f'CREATE OR REPLACE TABLE "{table_name}" AS '
            'SELECT * FROM read_csv_auto(?, header=true)', [str(source)]
        )
        return connection.execute(f'SELECT count(*) FROM "{table_name}"').fetchone()[0]
    finally:
        connection.close()