"""Data access for the dashboard: reads the dbt marts from DuckDB (read-only).
Each dataset is loaded once (lru_cache) when it is first needed, so the filters respond instantly."""
import time
from functools import lru_cache
from pathlib import Path

import duckdb
import pandas as pd
import requests
import truststore

truststore.inject_into_ssl()  # use Windows certificates (Avast HTTPS scanning), same as ingestion/ingest.py

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "polen.duckdb"
SNAPSHOT_DIR = Path(__file__).resolve().parents[1] / "data_snapshot"  # Parquet copy of the marts, in git

CITIES = ["Malmö", "Göteborg", "Stockholm", "Uppsala", "Umeå", "Luleå"]  # south -> north
# Same points as ingestion/config.py (latitude, longitude) – used for the live API call
CITY_COORDS = {"Malmö": (55.605, 13.003), "Göteborg": (57.709, 11.974), "Stockholm": (59.329, 18.069),
               "Uppsala": (59.858, 17.639), "Umeå": (63.826, 20.263), "Luleå": (65.584, 22.155)}
POLLEN = ["Alder", "Birch", "Grass", "Mugwort"]
WEATHER_POLLEN = ["Birch", "Grass", "Mugwort"]   # alder left out of weather analyses: weak data
ALL_CITIES = "All cities"

# High pollen day (daily average, grains/m³) – same thresholds as the analysis notebook
HIGH_THRESHOLD = {"Alder": 100, "Birch": 100, "Grass": 30, "Mugwort": 30}

# Plant photos in dashboard/assets/img (Wikimedia Commons, free licences – credited in the footer).
# Two photos per plant: the whole plant and the flowers/catkins that release the pollen.
# Type: alder and birch are trees; grass and mugwort are herbs (soft stems that grow back every year).
COMMONS = "https://commons.wikimedia.org/wiki/File:"
PLANT_PHOTOS = {
    "Alder": {
        "swedish": "al", "months": "Feb–Apr", "type_en": "Tree", "type_sv": "Träd",
        "plant": {"file": "img/alder_plant.jpg", "author": "AnRo0002", "licence": "CC0",
                  "url": COMMONS + "20160816Alnus_glutinosa1.jpg"},
        "flower": {"file": "img/alder_flower.jpg", "author": "AnRo0002", "licence": "CC0",
                   "url": COMMONS + "20180227Alnus_glutinosa1.jpg"},
    },
    "Birch": {
        "swedish": "björk", "months": "Apr–May", "type_en": "Tree", "type_sv": "Träd",
        "plant": {"file": "img/birch_plant.jpg", "author": "AnRo0002", "licence": "CC0",
                  "url": COMMONS + "20160816Betula_pendula1.jpg"},
        "flower": {"file": "img/birch_flower.jpg", "author": "DimiTalen", "licence": "CC BY-SA 3.0",
                   "url": COMMONS + "Betula_pendula_male_catkins.jpg"},
    },
    "Grass": {
        "swedish": "gräs", "months": "Jun–Aug", "type_en": "Herb (grass)", "type_sv": "Ört",
        "plant": {"file": "img/grass_plant.jpg", "author": "AnRo0002", "licence": "CC0",
                  "url": COMMONS + "20160702Phleum_pratense1.jpg"},
        "flower": {"file": "img/grass_flower.jpg", "author": "AnRo0002", "licence": "CC0",
                   "url": COMMONS + "20160702Phleum_pratense2.jpg"},
    },
    "Mugwort": {
        "swedish": "gråbo", "months": "Jul–Aug", "type_en": "Herb (weed)", "type_sv": "Ört",
        "plant": {"file": "img/mugwort_plant.jpg", "author": "AnRo0002", "licence": "CC0",
                  "url": COMMONS + "20190715Artemisia_vulgaris1.jpg"},
        "flower": {"file": "img/mugwort_flower.jpg", "author": "AnRo0002", "licence": "CC0",
                   "url": COMMONS + "20150822Artemisia_vulgaris1.jpg"},
    },
}


LIVE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
LIVE_CACHE_SECONDS = 15 * 60  # the model updates hourly: no need to call the API on every click
_live_cache = {}


def live_pollen(city):
    """Live pollen from the Open-Meteo API (not from DuckDB): the current hour plus hourly values for the
    last 2 days and the next 4 days (forecast). Cached 15 min per city. Returns (current, hourly, fetched_at)
    – fetched_at = when the API was called, Swedish time – or None if the API cannot be reached,
    so the dashboard keeps working offline."""
    cached = _live_cache.get(city)
    if cached and time.time() - cached[0] < LIVE_CACHE_SECONDS:
        return cached[1]
    variables = ",".join(f"{p.lower()}_pollen" for p in POLLEN)
    lat, lon = CITY_COORDS[city]
    try:
        r = requests.get(LIVE_URL, timeout=10, params={
            "latitude": lat, "longitude": lon, "hourly": variables, "current": variables,
            "timezone": "Europe/Stockholm", "past_days": 2, "forecast_days": 4})
        r.raise_for_status()
        j = r.json()
    except (requests.RequestException, ValueError):
        return None
    hourly = pd.DataFrame(j["hourly"]).assign(time=lambda d: pd.to_datetime(d["time"])).dropna(how="all", subset=variables.split(","))
    result = (j["current"], hourly, pd.Timestamp.now(tz="Europe/Stockholm"))
    _live_cache[city] = (time.time(), result)
    return result


POLLEN_META_URL = "https://air-quality-api.open-meteo.com/data/cams_europe/static/meta.json"
_release_cache = {}


def pollen_release_time():
    """Swedish time of day when the new pollen model run (CAMS Europe, once a day) is usually published,
    rounded to 30 min – e.g. '13:30' in summer, '12:30' in winter. Read from the Open-Meteo model metadata
    (cached 6 h); if it cannot be reached, the usual 11:30 UTC is used."""
    cached = _release_cache.get("time")
    if cached and time.time() - cached[0] < 6 * 3600:
        return cached[1]
    try:
        meta = requests.get(POLLEN_META_URL, timeout=5).json()
        published = pd.Timestamp(meta["last_run_availability_time"], unit="s", tz="UTC")
    except (requests.RequestException, ValueError, KeyError):
        published = pd.Timestamp.now(tz="UTC").normalize() + pd.Timedelta(hours=11, minutes=30)
    local = published.tz_convert("Europe/Stockholm").round("30min")
    text = f"{local:%H:%M}"
    _release_cache["time"] = (time.time(), text)
    return text


POLLEN_COLUMNS = [f"{p.lower()}_pollen" for p in POLLEN]   # same names in marts.hourly and the live API
DAYS_BEFORE, DAYS_AFTER = 2, 4   # window of the week chart: same as the live API call (past_days, forecast_days)


def _hourly_window(city, start, end):
    """Hourly pollen from marts.hourly for one city, Swedish time, start <= time < end."""
    if city not in CITY_COORDS:   # the city ends up in the SQL text, so only accept known cities
        raise ValueError(f"unknown city {city!r}")
    hourly = query(f"""
        SELECT time_local AS time, {', '.join(POLLEN_COLUMNS)}
        FROM marts.hourly
        WHERE city = '{city}' AND time_local >= '{start:%Y-%m-%d}' AND time_local < '{end:%Y-%m-%d}'
        ORDER BY time_local
    """)
    hourly["time"] = pd.to_datetime(hourly["time"])
    return hourly


def _typical_window(city, start, end):
    """Typical hourly pollen for a window of dates = average of the same calendar dates in every year with
    complete data (climatology). Returns (hourly, list of the years used)."""
    coverage = data_coverage()
    frames, years = [], []
    for year in range(coverage["first_day"].year, coverage["last_day"].year + 1):
        shift = pd.DateOffset(years=year - start.year)
        s, e = start + shift, end + shift
        if s < coverage["first_day"] or e > coverage["last_day"] + pd.Timedelta(days=1):
            continue   # that year does not cover the whole window
        frame = _hourly_window(city, s, e)
        frame["time"] = frame["time"] - s + start   # move that year's hours onto the selected dates
        frames.append(frame)
        years.append(year)
    if not frames:
        return pd.DataFrame(columns=["time", *POLLEN_COLUMNS]), []
    typical = pd.concat(frames).groupby("time", as_index=False)[POLLEN_COLUMNS].mean()
    return typical, years


def pollen_for_date(city, day):
    """Hourly pollen around `day` (2 days before → 4 days after) for the Pollen now charts, from the best
    source for that date:
    - 'live'     – today: the Open-Meteo API (current hour + last 2 days + forecast)
    - 'history'  – a past day in the database (marts.hourly)
    - 'recent'   – a past day not in the database yet (the API keeps the last 2 days)
    - 'forecast' – one of the next days covered by the API forecast
    - 'typical'  – any other future day: average of the same dates in the years with data
    Returns a dict with 'kind' and 'hourly' (+ 'current', 'fetched_at' or 'years' = list of years averaged),
    or None when the live
    API is needed but cannot be reached."""
    real_today = pd.Timestamp.now(tz="Europe/Stockholm").date()
    start = pd.Timestamp(day) - pd.Timedelta(days=DAYS_BEFORE)
    end = pd.Timestamp(day) + pd.Timedelta(days=DAYS_AFTER + 1)
    if day == real_today:
        live = live_pollen(city)
        if live is None:
            return None
        current, hourly, fetched_at = live
        return {"kind": "live", "hourly": hourly, "current": current, "fetched_at": fetched_at}
    if day <= data_coverage()["last_day"].date():
        return {"kind": "history", "hourly": _hourly_window(city, start, end)}
    live = live_pollen(city)
    if live is not None and (live[1]["time"].dt.date == day).any():
        return {"kind": "forecast" if day > real_today else "recent", "hourly": live[1], "fetched_at": live[2]}
    typical, years = _typical_window(city, start, end)
    return {"kind": "typical", "hourly": typical, "years": years}


def query(sql):
    """Run SQL and return a DataFrame. Opens and closes the connection each time,
    so dbt / ingest.py are never blocked by the dashboard.
    Without data/polen.duckdb (a fresh clone or the published dashboard), the same SQL runs on the
    Parquet snapshot in data_snapshot/ (see export_snapshot.py): each file becomes a view marts.<table>."""
    if DB_PATH.exists():
        with duckdb.connect(str(DB_PATH), read_only=True) as con:
            return con.sql(sql).df()
    with duckdb.connect() as con:
        con.execute("CREATE SCHEMA marts")
        for path in SNAPSHOT_DIR.glob("*.parquet"):
            con.execute(f"CREATE VIEW marts.{path.stem} AS SELECT * FROM '{path.as_posix()}'")
        return con.sql(sql).df()


def data_coverage():
    """Cities, pollen types and period covered by the data (for the KPIs on the first tab)."""
    row = query("""
        SELECT count(DISTINCT city) AS n_cities, min(date_local) AS first_day, max(date_local) AS last_day
        FROM marts.daily
    """).iloc[0]
    return {"n_cities": int(row["n_cities"]), "n_pollen": len(POLLEN),
            "first_day": pd.Timestamp(row["first_day"]), "last_day": pd.Timestamp(row["last_day"])}


# ---------------------------------------------------------------------------
# Datasets for the charts (loaded once). Callers must not modify the returned frames.
# ---------------------------------------------------------------------------
@lru_cache
def risk_calendar_by_year():
    """Share of days with high pollen (any type) per city, year and ISO week (March–September) – one row per
    year when the Pollen calendar shows a single city."""
    d = daily()
    d = d[d["week"].between(10, 38)]
    return d.groupby(["city", "year", "week"], as_index=False)["high_any"].mean()


@lru_cache
def weekly_by_year():
    """Average daily pollen per city, ISO year and ISO week (long format) – one row per year when the
    Pollen calendar shows a single city."""
    w = query("SELECT * FROM marts.weekly WHERE iso_week <= 52")
    long = w.melt(id_vars=["city", "iso_year", "iso_week"], value_vars=[f"{p.lower()}_pollen_avg" for p in POLLEN],
                  var_name="pollen_type", value_name="grains")
    long["pollen_type"] = long["pollen_type"].str.replace("_pollen_avg", "").str.capitalize()
    return long


@lru_cache
def weekly():
    """Average daily pollen per city and ISO week, averaged over all years (long format)."""
    w = query("SELECT * FROM marts.weekly WHERE iso_week <= 52")
    long = w.melt(id_vars=["city", "iso_week"], value_vars=[f"{p.lower()}_pollen_avg" for p in POLLEN],
                  var_name="pollen_type", value_name="grains")
    long["pollen_type"] = long["pollen_type"].str.replace("_pollen_avg", "").str.capitalize()
    return long.groupby(["pollen_type", "city", "iso_week"], as_index=False)["grains"].mean()


@lru_cache
def seasons():
    """One row per city, pollen type and year: start, peak, end (marts.seasons) + day of year."""
    s = query("SELECT * FROM marts.seasons")
    s["pollen_type"] = s["pollen_type"].str.capitalize()
    for col in ["season_start", "peak_date", "season_end"]:
        s[col] = pd.to_datetime(s[col])
        s[col.replace("_date", "").replace("season_", "") + "_doy"] = s[col].dt.dayofyear
    return s


@lru_cache
def typical_seasons():
    """Typical season per city and pollen type = median day of year over 2021–2026."""
    return seasons().groupby(["pollen_type", "city"], as_index=False)[["start_doy", "peak_doy", "end_doy"]].median()


@lru_cache
def hourly_profile():
    """Average pollen per hour of the day on season days, as an index (100 = that city's daily average)."""
    h = query("""
        WITH h AS (
            SELECT h.*, s.pollen_type
            FROM marts.hourly h
            JOIN marts.seasons s
              ON s.city = h.city AND s.year = year(h.date_local)
             AND h.date_local BETWEEN s.season_start AND s.season_end
        )
        SELECT city, pollen_type, hour_local,
               avg(CASE pollen_type WHEN 'alder' THEN alder_pollen WHEN 'birch' THEN birch_pollen
                                    WHEN 'grass' THEN grass_pollen ELSE mugwort_pollen END) AS grains
        FROM h
        GROUP BY ALL
    """)
    h["pollen_type"] = h["pollen_type"].str.capitalize()
    h["index"] = h["grains"] / h.groupby(["city", "pollen_type"])["grains"].transform("mean") * 100
    return h.sort_values(["city", "pollen_type", "hour_local"])


@lru_cache
def daily():
    """Daily mart with date parts and high/moderate pollen flags."""
    d = query("SELECT * FROM marts.daily")
    d["date_local"] = pd.to_datetime(d["date_local"])
    d["year"] = d["date_local"].dt.year
    d["month"] = d["date_local"].dt.month
    d["week"] = d["date_local"].dt.isocalendar().week.astype(int)
    for p in POLLEN:
        d[f"high_{p}"] = d[f"{p.lower()}_pollen_avg"] > HIGH_THRESHOLD[p]
    d["high_any"] = d[[f"high_{p}" for p in POLLEN]].any(axis=1)
    return d


@lru_cache
def risk_calendar():
    """Share of days with high pollen (any type) per city and ISO week (March–September)."""
    d = daily()
    d = d[d["week"].between(10, 38)]
    return d.groupby(["city", "week"], as_index=False)["high_any"].mean()


@lru_cache
def season_days():
    """Daily data inside each season (birch, grass, mugwort) with ratio = pollen / season average."""
    d = query("""
        SELECT d.*, s.pollen_type, s.year,
               CASE s.pollen_type WHEN 'birch' THEN d.birch_pollen_avg
                                  WHEN 'grass' THEN d.grass_pollen_avg ELSE d.mugwort_pollen_avg END AS grains
        FROM marts.daily d
        JOIN marts.seasons s
          ON s.city = d.city AND d.date_local BETWEEN s.season_start AND s.season_end
        WHERE s.pollen_type IN ('birch', 'grass', 'mugwort')
    """)
    d["pollen_type"] = d["pollen_type"].str.capitalize()
    d["ratio"] = d["grains"] / d.groupby(["city", "pollen_type", "year"])["grains"].transform("mean")
    d["Rain"] = pd.cut(d["precipitation_mm"], [-1, 0.1, 2, 1000], labels=["Dry", "Light rain", "Rainy"])
    d["Wind"] = pd.cut(d["wind_speed_avg_kmh"], [-1, 10, 15, 20, 1000], labels=["<10 km/h", "10–15", "15–20", ">20 km/h"])
    d["Temperature"] = pd.cut(d["temperature_max_c"], [-50, 10, 15, 20, 25, 50],
                              labels=["<10 °C", "10–15", "15–20", "20–25", ">25 °C"])
    return d


@lru_cache
def rain_events():
    """Rain events inside the season: ≥ 2 mm after a dry day. Recovery = first day back to ≥ 80%."""
    d = query("SELECT * FROM marts.daily ORDER BY city, date_local")
    s = query("SELECT * FROM marts.seasons WHERE pollen_type IN ('birch', 'grass', 'mugwort')")
    by_city = {c: g.reset_index(drop=True) for c, g in d.groupby("city")}
    events = []
    for season in s.itertuples():
        col = f"{season.pollen_type}_pollen_avg"
        c = by_city[season.city]
        in_season = c.index[(c["date_local"] >= season.season_start) & (c["date_local"] <= season.season_end)]
        for i in in_season:
            if i == 0 or i + 7 >= len(c):
                continue
            if c.at[i, "precipitation_mm"] < 2 or c.at[i - 1, "precipitation_mm"] >= 0.1 or c.at[i - 1, col] < 1:
                continue
            before = c.at[i - 1, col]
            recovered = next((k for k in range(1, 8) if c.at[i + k, col] >= 0.8 * before), None)
            events.append({"city": season.city, "pollen_type": season.pollen_type.capitalize(),
                           "drop": c.at[i, col] / before, "recovery_days": recovered})
    return pd.DataFrame(events)


@lru_cache
def risk_days():
    """Days with high pollen (any type) AND bad air (WHO: PM2.5 > 15 or ozone 8-hour > 100 µg/m³)."""
    r = query("""
        WITH ozone_8h AS (
            SELECT city, date_local, max(o3_8h) AS ozone_8h_max
            FROM (SELECT city, date_local,
                         avg(ozone) OVER (PARTITION BY city ORDER BY time_utc
                                          ROWS BETWEEN 7 PRECEDING AND CURRENT ROW) AS o3_8h
                  FROM marts.hourly)
            GROUP BY ALL
        )
        SELECT d.city, d.date_local, d.pm2_5_avg, o.ozone_8h_max
        FROM marts.daily d JOIN ozone_8h o USING (city, date_local)
    """)
    r["date_local"] = pd.to_datetime(r["date_local"])
    r = r.merge(daily()[["city", "date_local", "high_any", "year", "month"]], on=["city", "date_local"])
    r["bad_ozone"] = r["ozone_8h_max"] > 100
    r["bad_pm25"] = r["pm2_5_avg"] > 15
    r["both"] = r["high_any"] & (r["bad_ozone"] | r["bad_pm25"])
    r["cause"] = r["bad_ozone"].map({True: "Ozone", False: "PM2.5 (fine particles)"})
    return r


# ---------------------------------------------------------------------------
# Business tabs (Q2, Q7–Q12 of notebooks/analysis.ipynb)
# ---------------------------------------------------------------------------
@lru_cache
def stock_plan():
    """Per pollen type and city: stock ready by week (1 week before the 10th-percentile start week),
    typical start / peak / end week and average yearly pollen (Q8)."""
    plan = (seasons().groupby(["pollen_type", "city"])
            .agg(earliest_start=("start_week", lambda w: w.quantile(0.1)),
                 typical_start=("start_week", "median"), typical_peak=("peak_week", "median"),
                 typical_end=("end_week", "median"), yearly_pollen=("year_total", "mean"))
            .reset_index())
    plan["stock_ready_week"] = (plan["earliest_start"] - 1).round().astype(int)
    return plan


@lru_cache
def season_coverage():
    """Share of years each ISO week (5–36) was inside the season, per pollen type and city (Q8)."""
    weeks = pd.DataFrame({"week": range(5, 37)})
    s = seasons()[["city", "pollen_type", "year", "start_week", "end_week"]]
    cov = s.merge(weeks, how="cross")
    cov["in_season"] = (cov["week"] >= cov["start_week"]) & (cov["week"] <= cov["end_week"])
    return cov.groupby(["pollen_type", "city", "week"], as_index=False)["in_season"].mean()


@lru_cache
def start_gaps():
    """Weeks between each city's season start and Malmö's, same year and pollen type (Q2)."""
    s = seasons()[["city", "pollen_type", "year", "season_start"]]
    malmo = s[s["city"] == "Malmö"].rename(columns={"season_start": "malmo_start"}).drop(columns="city")
    g = s.merge(malmo, on=["pollen_type", "year"])
    g["gap_weeks"] = (g["season_start"] - g["malmo_start"]).dt.days / 7
    return g.groupby(["pollen_type", "city"], as_index=False)["gap_weeks"].agg(
        median="median", earliest="min", latest="max")


@lru_cache
def intensity():
    """Season intensity index per city, pollen type and year (100 = that city's average year) (Q7)."""
    s = seasons()[["city", "pollen_type", "year", "year_total"]].copy()
    s["index"] = s["year_total"] / s.groupby(["city", "pollen_type"])["year_total"].transform("mean") * 100
    return s


HALF_MONTHS = ["Apr 1–15", "Apr 16–end", "May 1–15", "May 16–end", "Jun 1–15", "Jun 16–end"]


@lru_cache
def tourism():
    """Share of high-pollen days per city and half-month of spring (Q9)."""
    d = daily()
    d = d[d["month"].isin([4, 5, 6])].copy()
    d["period"] = d["date_local"].dt.strftime("%b") + d["date_local"].dt.day.map(lambda x: " 1–15" if x <= 15 else " 16–end")
    return d.groupby(["city", "period"], as_index=False)["high_any"].mean()


@lru_cache
def spring_risk():
    """Share of high-pollen days over the whole spring (April–June) per city (Q9)."""
    d = daily()
    return d[d["month"].isin([4, 5, 6])].groupby("city", as_index=False)["high_any"].mean()


@lru_cache
def event_factors():
    """Share of days per ISO week (14–38) with rain ≥ 1 mm, bad air or heat ≥ 25 °C, average of the 6 cities (Q10)."""
    d = daily()[["city", "date_local", "week", "precipitation_mm", "temperature_max_c"]]
    d = d.merge(risk_days()[["city", "date_local", "bad_ozone", "bad_pm25"]], on=["city", "date_local"])
    d = d[d["week"].between(14, 38)].copy()
    d["Rain (≥ 1 mm)"] = d["precipitation_mm"] >= 1
    d["Bad air (PM2.5 or ozone)"] = d["bad_ozone"] | d["bad_pm25"]
    d["Hot (≥ 25 °C)"] = d["temperature_max_c"] >= 25
    factors = ["Rain (≥ 1 mm)", "Bad air (PM2.5 or ozone)", "Hot (≥ 25 °C)"]
    return d.groupby("week")[factors].mean().reset_index().melt(id_vars="week", var_name="factor", value_name="share")


@lru_cache
def event_risk():
    """Share of 'problem days' per city and ISO week 14–38: pollen (any type) > 10 grains/m³,
    rain ≥ 1 mm or bad air (Q10)."""
    d = daily()[["city", "date_local", "week", "precipitation_mm"] + [f"{p.lower()}_pollen_avg" for p in POLLEN]]
    d = d.merge(risk_days()[["city", "date_local", "bad_ozone", "bad_pm25"]], on=["city", "date_local"])
    d = d[d["week"].between(14, 38)]
    pollen = (d[[f"{p.lower()}_pollen_avg" for p in POLLEN]] > 10).any(axis=1)
    d["problem"] = pollen | (d["precipitation_mm"] >= 1) | d["bad_ozone"] | d["bad_pm25"]
    return d.groupby(["city", "week"], as_index=False)["problem"].mean()


@lru_cache
def retail_need():
    """Average days per month with high pollen and with PM2.5 above the WHO limit, per city (Q11)."""
    d = daily()[["city", "date_local", "month", "high_any", "pm2_5_avg"]].copy()
    d["bad_pm25"] = d["pm2_5_avg"] > 15
    need = d.groupby(["city", "month"], as_index=False)[["high_any", "bad_pm25"]].mean()
    need["high_days"] = need["high_any"] * 30.4
    need["pm25_days"] = need["bad_pm25"] * 30.4
    return need


# ---------------------------------------------------------------------------
# Official facts for the "Why this matters" tab (see notebooks/info_project.md)
# ---------------------------------------------------------------------------
SOURCES = {
    "1177": ("1177 – Pollenallergi",
             "https://www.1177.se/sjukdomar--besvar/allergier-och-overkanslighet/pollenallergi/"),
    "CAMM 2026": ("CAMM, Region Stockholm (2026) – Förändringar i pollensäsonger, klimat och folkhälsa",
                  "https://www.folkhalsoguiden.se/49c72d/globalassets/verksamheter/forskning-och-utveckling/"
                  "centrum-for-arbets--och-miljomedicin1/rapporter/pollenrapport_klar.pdf"),
    "MHR 2025": ("CAMM Miljöhälsorapport 2025, ch. 12 (Miljöhälsoenkäten, Folkhälsomyndigheten)",
                 "https://www.camm.regionstockholm.se/rapporter-och-faktablad/rapporter/miljohalsorapporter/"
                 "miljohalsorapport-2025/12-allergi-och-sjukdomar-i-luftvagarna/"),
}

KPIS = [
    {"value": "1 in 4", "label": "Swedes get pollen symptoms in spring and summer", "source": "1177"},
    {"value": "43%", "label": "of adults in Stockholm County report pollen allergy (2023)", "source": "MHR 2025"},
    {"value": "~16 days", "label": "earlier birch season than in the 1970s (Stockholm)", "source": "CAMM 2026"},
    {"value": "~13 bn SEK", "label": "yearly cost of pollen-related health effects in Sweden", "source": "CAMM 2026"},
]

# Share of adults in Stockholm County with pollen allergy (Miljöhälsoenkäten)
PREVALENCE = pd.DataFrame({"group": ["2007", "2023"], "percent": [30, 43]})

# Change in Stockholm pollen seasons since the early 1970s (CAMM 2026 p. 17 and Table B1)
SEASON_CHANGE = pd.DataFrame({"change": ["Birch season starts", "Grass season lasts", "Mugwort season lasts"],
                              "days": [-16, 19, 40],
                              "label": ["16 days earlier", "19 days longer", "40 days longer"]})
