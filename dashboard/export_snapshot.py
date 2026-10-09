"""Export the dbt marts the dashboard reads to Parquet files in data_snapshot/.

The DuckDB database (data/) is not in git, so a published dashboard (e.g. on Render) or a fresh clone
has no data. These Parquet files (~5 MB) are committed instead; dashboard/data.py reads them when
data/polen.duckdb does not exist.

Run after ingestion + dbt:  uv run python dashboard/export_snapshot.py
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "polen.duckdb"
SNAPSHOT_DIR = ROOT / "data_snapshot"
TABLES = ["hourly", "daily", "weekly", "seasons", "missing_values"]


def main():
    SNAPSHOT_DIR.mkdir(exist_ok=True)
    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        for table in TABLES:
            path = SNAPSHOT_DIR / f"{table}.parquet"
            con.execute(f"COPY marts.{table} TO '{path.as_posix()}' (FORMAT parquet, COMPRESSION zstd)")
            print(f"marts.{table} -> {path.relative_to(ROOT)} ({path.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
