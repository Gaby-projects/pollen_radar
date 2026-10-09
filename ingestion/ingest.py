"""Download pollen, air quality and weather data and load it into DuckDB (raw layer).

Usage:  uv run python ingestion/ingest.py
"""
import logging
from datetime import date, datetime, timedelta, timezone

import duckdb
import pandas as pd
import requests
import truststore
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import ACTIVE_CITIES, CITIES, DB_PATH, LOG_PATH, SOURCES, START_DATE

truststore.inject_into_ssl()  # use Windows certificates (Avast HTTPS scanning)

log = logging.getLogger("ingest")


def setup_logging():
    LOG_PATH.parent.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler()],
    )


def make_session():
    """HTTP session that retries on rate limits (429) and server errors (5xx)."""
    retry = Retry(
        total=5,
        backoff_factor=2,  # waits 2, 4, 8, 16... seconds between attempts
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def create_tables(con):
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    for name, source in SOURCES.items():
        columns = ", ".join(f"{var} DOUBLE" for var in source["variables"])
        con.execute(f"""
            CREATE TABLE IF NOT EXISTS raw.{name} (
                city      VARCHAR,
                time      TIMESTAMP,  -- UTC
                {columns},
                loaded_at TIMESTAMP,  -- UTC
                PRIMARY KEY (city, time)
            )
        """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw.ingestion_log (
            run_at      TIMESTAMP,
            source      VARCHAR,
            city        VARCHAR,
            start_date  DATE,
            end_date    DATE,
            rows_loaded INTEGER,
            status      VARCHAR,
            error       VARCHAR
        )
    """)


def next_start_date(con, source, city):
    """First day to download: START_DATE on the first run, else the last stored day.

    The last day is downloaded again because it may be incomplete;
    the primary key makes the overlap replace rows instead of duplicating them.
    """
    last = con.execute(f"SELECT max(time) FROM raw.{source} WHERE city = ?", [city]).fetchone()[0]
    return START_DATE if last is None else last.date()


def year_chunks(start, end):
    """Split a date range into one request per calendar year to keep responses small."""
    while start <= end:
        chunk_end = min(date(start.year, 12, 31), end)
        yield start, chunk_end
        start = chunk_end + timedelta(days=1)


def fetch(session, source, lat, lon, start, end):
    variables = SOURCES[source]["variables"]
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(variables),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "timezone": "GMT",  # UTC avoids duplicate hours when clocks change; staging converts to Stockholm time
    }
    response = session.get(SOURCES[source]["url"], params=params, timeout=60)
    response.raise_for_status()

    df = pd.DataFrame(response.json()["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    # Drop hours with no values yet (e.g. weather archive lags a few days);
    # they are picked up by a later run.
    return df.dropna(subset=variables, how="all")


def save(con, source, city, df):
    df.insert(0, "city", city)
    df["loaded_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
    con.register("new_rows", df)
    con.execute(f"INSERT OR REPLACE INTO raw.{source} BY NAME SELECT * FROM new_rows")
    con.unregister("new_rows")
    return len(df)


def main():
    setup_logging()
    DB_PATH.parent.mkdir(exist_ok=True)
    end = date.today() - timedelta(days=1)  # only past data, no forecasts
    session = make_session()
    failures = 0

    with duckdb.connect(str(DB_PATH)) as con:
        create_tables(con)

        for city in ACTIVE_CITIES:
            lat, lon = CITIES[city]
            for source in SOURCES:
                start = next_start_date(con, source, city)
                rows, status, error = 0, "ok", None
                try:
                    for chunk_start, chunk_end in year_chunks(start, end):
                        df = fetch(session, source, lat, lon, chunk_start, chunk_end)
                        rows += save(con, source, city, df)
                except Exception as exc:
                    status, error = "error", str(exc)
                    failures += 1
                    log.exception("%s / %s failed", city, source)

                con.execute(
                    "INSERT INTO raw.ingestion_log VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    [datetime.now(timezone.utc).replace(tzinfo=None), source, city,
                     start, end, rows, status, error],
                )
                log.info("%s / %s: %s to %s, %d rows, %s", city, source, start, end, rows, status)

    if failures:
        raise SystemExit(1)  # non-zero exit code -> GitHub Actions marks the run as failed


if __name__ == "__main__":
    main()
