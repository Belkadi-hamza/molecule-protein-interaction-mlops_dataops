import duckdb

from data_contract import FEATURE_TABLE, SHARED_COLUMNS, TARGET_COLUMN


def validate_features(
    database_path: str = "/data/warehouse.duckdb",
    table_name: str = FEATURE_TABLE,
) -> int:
    connection = duckdb.connect(database_path)
    try:
        columns = [row[0] for row in connection.execute(
            f'DESCRIBE "{table_name}"'
        ).fetchall()]
        missing = sorted(set(SHARED_COLUMNS) - set(columns))
        if missing:
            raise ValueError(f"Feature table is missing columns: {', '.join(missing)}")
        rows, classes = connection.execute(
            f'SELECT count(*), count(DISTINCT "{TARGET_COLUMN}") FROM "{table_name}" '
            f'WHERE "{TARGET_COLUMN}" IS NOT NULL'
        ).fetchone()
        if rows == 0 or classes < 2:
            raise ValueError("Training data must contain rows from at least two classes")
        return rows
    finally:
        connection.close()