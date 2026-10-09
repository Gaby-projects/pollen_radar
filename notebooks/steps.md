# Project steps

| Step | What | Phase | Status |
|---|---|---|---|
| Step 1 | Check the data: how many years of pollen does the API have? | Phase 0 – Validate | ✅ Done (pollen from late 2020; period 2021 → yesterday) |
| Step 2 | Download pollen, pollution and weather for 6 Swedish cities | Phase 1 – Ingestion | ✅ Done (`ingestion/ingest.py`) |
| Step 3 | Store the data as it arrives in DuckDB | Phase 1 – Ingestion | ✅ Done (`data/polen.duckdb`, schema `raw`) |
| Step 4 | Clean and join the data with dbt (one table per city and hour) and calculate start/end of each pollen season | Phase 2 – Transformation | ✅ Done (run: `cd dbt` → `uv run dbt run`) |
| Step 4a | dbt setup + `staging`: Swedish time, empty pollen → 0, clean column names | Phase 2 – Transformation | ✅ Done (`staging.stg_air_quality`, `staging.stg_weather`) |
| Step 4b | `marts`: hourly table (pollen + pollution + weather) + daily and weekly tables | Phase 2 – Transformation | ✅ Done (`marts.hourly`, `marts.daily`, `marts.weekly`) |
| Step 4c | Seasons table: start (5%), peak and end (95%) per city, year and pollen type | Phase 2 – Transformation | ✅ Done (`marts.seasons`) |
| Step 5 | Automatic tests that warn about missing data or errors | Phase 3 – Data quality | ✅ Done (58 tests pass; run: `cd dbt` → `uv run dbt build` + `uv run dbt source freshness`) |
| Step 5b | Python tests for the live API call (mocked HTTP: API OK, API down, cache) | Phase 3 – Data quality | ✅ Done (`tests/test_live_api.py`, 6 tests + `tests/test_alerts.py`, 17 tests + `tests/test_calendar.py`, 2 tests + `tests/test_update.py`, 5 tests + `tests/test_notify.py`, 7 tests = 39; run: `uv run pytest`) |
| Step 8b | Pollen alerts: "season coming within 14 days" + "forecast ≥ 10 grains/m³ for 3 hours in a row", as a Windows notification, a phone push via ntfy (one channel for all cities: pollen-project-gab) and a traffic-light alert bar (🟢🟡🔴) per city and date in the "Pollen now" tab, with real data for past dates | Phase 6 – Dashboard | ✅ Done (`dashboard/alerts.py`, `dashboard/notify.py`, 17 tests in `tests/test_alerts.py`; test: `uv run python dashboard/notify.py --city Stockholm --date 2026-04-02`) |
| Step 8c | "Update data" button in the dashboard header: runs ingest → dbt build → snapshot and reloads; greyed out (disabled) when the data already goes up to yesterday | Phase 6 – Dashboard | ✅ Done (`dashboard/update.py`, local only) |
| Step 6 | GitHub Actions runs the pipeline every day | Phase 4 – Automation | ⬜ Pending (done at the end, together with Step 9: needs GitHub) |
| Step 7 | Answer the questions: when pollen is highest, best hour of the day, effect of rain and wind, south vs north | Phase 5 – Analysis | ✅ Done (`notebooks/analysis.ipynb`: EDA + Q1–Q12 with charts, CAMM validation, recommendations) |
| Step 7b | Retail A/B test design: does a campaign that follows the pollen season sell more than one that follows the calendar? Geo-experiment (regions or stores as groups), using the season start per region (`marts.seasons`). Other ideas: pollen alert email, pollen banner, product placement at the checkout | Phase 5 – Analysis | ✅ Done (Q12 in `analysis.ipynb`: real-time pollen trigger + geo-experiment design + store sample size; no sales data) |
| Step 8 | Dashboard in **Dash (Plotly)**: pollen calendar for allergy sufferers + stock view for pharmacies (+ tourism, events, retail) | Phase 6 – Dashboard | ✅ Done locally (8 tabs: Why this matters · Pollen calendar · Weather & air · Pharmacies · Tourism · Events · Retail (incl. A/B test ideas) · Pollen now (photos, alert traffic light, charts for the selected date – live only for today)). Publishing online in Step 9. Run: `uv run python dashboard/app.py` → http://127.0.0.1:8050 |
| Step 9 | Clear README on GitHub, published dashboard and LinkedIn post | Phase 6 – Presentation | 🟡 In progress (README written locally, not pushed yet; screenshots, publishing and LinkedIn post pending) |
