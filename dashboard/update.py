"""'Update data' button: run the pipeline from the dashboard and reload the cached datasets.

Same steps as by hand:  ingestion/ingest.py → dbt build → dashboard/export_snapshot.py
Only available locally (needs data/polen.duckdb); on Render the dashboard reads the Parquet snapshot instead.
"""
import os
import subprocess
import sys
from functools import _lru_cache_wrapper
from pathlib import Path

import pandas as pd

import data

ROOT = Path(__file__).resolve().parents[1]
STEP_TIMEOUT = 10 * 60   # seconds per step; the first full download of 6 years takes a few minutes

# (name shown to the user, command, working folder) – same Python as the dashboard, so no `uv run` needed
STEPS = [
    ("Download new data (ingest.py)", [sys.executable, "ingestion/ingest.py"], ROOT),
    ("Rebuild and test tables (dbt build)", [sys.executable, "-m", "dbt.cli.main", "build"], ROOT / "dbt"),
    ("Refresh Parquet snapshot", [sys.executable, "dashboard/export_snapshot.py"], ROOT),
]


def can_update():
    """The button needs the local DuckDB database (not available on Render)."""
    return data.DB_PATH.exists()


def last_update():
    """When the ingestion last ran (Swedish time) and the last day of data, for the header."""
    coverage = data.data_coverage()
    ran_at = None
    if can_update():
        run = data.query("SELECT max(run_at) AS run_at FROM raw.ingestion_log").iloc[0]["run_at"]
        if pd.notna(run):
            ran_at = pd.Timestamp(run).tz_localize("UTC").tz_convert("Europe/Stockholm")
    return ran_at, coverage["last_day"]


def days_behind(last_day, today=None):
    """Days of data missing: the ingestion downloads up to yesterday, so 0 = up to date."""
    today = today or pd.Timestamp.now(tz="Europe/Stockholm").date()
    yesterday = today - pd.Timedelta(days=1)
    return max((yesterday - pd.Timestamp(last_day).date()).days, 0)


def clear_caches():
    """Forget every dataset cached in data.py (lru_cache) and the live API answers, so new data is read."""
    for value in vars(data).values():
        if isinstance(value, _lru_cache_wrapper):
            value.cache_clear()
    data._live_cache.clear()


def run_update():
    """Run the three steps in order and stop at the first failure.
    Returns (ok, list of (step name, ok, last lines of output))."""
    results = []
    for name, command, folder in STEPS:
        try:
            done = subprocess.run(command, cwd=folder, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=STEP_TIMEOUT,
                                  env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            ok = done.returncode == 0
            output = (done.stdout + done.stderr).strip().splitlines()[-3:]
        except subprocess.TimeoutExpired:
            ok, output = False, [f"stopped after {STEP_TIMEOUT // 60} minutes"]
        results.append((name, ok, output))
        if not ok:
            return False, results
    clear_caches()
    return True, results
