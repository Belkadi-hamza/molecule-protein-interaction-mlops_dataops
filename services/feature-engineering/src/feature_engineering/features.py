import duckdb

from data_contract import FEATURE_TABLE, RAW_TABLE, SHARED_COLUMNS


def build_features(
    database_path: str = "/data/warehouse.duckdb",
    source_table: str = RAW_TABLE,
    feature_table: str = FEATURE_TABLE,
) -> int:
    connection = duckdb.connect(database_path)
    try:
        selected_columns = ", ".join(f'"{column}"' for column in SHARED_COLUMNS)
        connection.execute(
            f'''CREATE OR REPLACE TABLE "{feature_table}" AS
                SELECT {selected_columns},
                       ln(1 + abs(CAST(affinity_value AS DOUBLE))) AS affinity_log_value
                FROM "{source_table}"
                WHERE affinity_value IS NOT NULL'''
        )
        return connection.execute(f'SELECT count(*) FROM "{feature_table}"').fetchone()[0]
    finally:
        connection.close()