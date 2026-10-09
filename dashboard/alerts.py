"""Pollen alerts: one logic, used by the Windows notification (notify.py) and the dashboard alert bar.

Two kinds of alert per city:
- "coming"   – a pollen season usually starts within the next 14 days (typical start = median 2021–2026).
               1177: allergy treatment works best when started 1–2 weeks before the season.
- "forecast" – the live 4-day forecast (Open-Meteo API) shows a pollen type at or above 10 grains/m³
               (where symptoms start) for 3 hours in a row. Same 'persistence' idea as alert_logic.py
               in the padel case: one hour above the level could be noise, several in a row is a signal.
"""
import datetime as dt
import os

import pandas as pd

from data import POLLEN, live_pollen, seasons, typical_seasons

# ntfy push notifications: ONE channel (topic) for all six cities – every alert names its city in the title.
# Anyone who knows a topic name can read it, so it is a not-obvious name; it can be changed with the NTFY_TOPIC
# environment variable without touching the code.
NTFY_SERVER = "https://ntfy.sh"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "pollen-project-gab")
NTFY_TAGS = {"Alder": "deciduous_tree", "Birch": "deciduous_tree", "Grass": "ear_of_rice", "Mugwort": "herb"}


def ntfy_topic(city=None):
    """The ntfy channel for the alerts. One channel for all cities, so `city` is not needed; it is kept so
    callers can stay the same if the project ever goes back to one channel per city."""
    return NTFY_TOPIC


WARN_DAYS = 14          # warn this many days (or fewer) before the typical season start
SYMPTOM_LEVEL = 10      # grains/m³, same level as the "symptoms start" line in the live charts
PERSISTENCE_HOURS = 3   # hours in a row at or above SYMPTOM_LEVEL before a forecast alert
ICONS = {"Alder": "🌳", "Birch": "🌳", "Grass": "🌾", "Mugwort": "🌿"}


def _doy_to_date(doy, year):
    return dt.date(year, 1, 1) + dt.timedelta(days=int(round(doy)) - 1)


def coming_alerts(city, today):
    """Seasons that typically start in 1–WARN_DAYS days from `today` in this city, soonest first."""
    typical = typical_seasons().query("city == @city").set_index("pollen_type")
    # range of the real start dates over the years with data, e.g. birch in Stockholm: 3 Apr (2025) – 27 Apr (2022)
    history = seasons().query("city == @city").groupby("pollen_type").agg(
        earliest=("start_doy", "min"), latest=("start_doy", "max"), first_year=("year", "min"), last_year=("year", "max"))
    alerts = []
    for pollen in POLLEN:
        start = _doy_to_date(typical.loc[pollen, "start_doy"], today.year)
        days = (start - today).days
        if 0 < days <= WARN_DAYS:
            h = history.loc[pollen]
            alerts.append({"kind": "coming", "city": city, "pollen": pollen, "days": days, "start": start,
                           "earliest": _doy_to_date(h["earliest"], today.year),
                           "latest": _doy_to_date(h["latest"], today.year),
                           "years": f"{h['first_year']}–{h['last_year']}"})
    return sorted(alerts, key=lambda a: a["days"])


def in_season(city, today):
    """Pollen types whose typical season (median start → median end, 2021–2026) includes `today`."""
    typical = typical_seasons().query("city == @city").set_index("pollen_type")
    seasons_now = []
    for pollen in POLLEN:
        start = _doy_to_date(typical.loc[pollen, "start_doy"], today.year)
        end = _doy_to_date(typical.loc[pollen, "end_doy"], today.year)
        if start <= today <= end:
            seasons_now.append({"pollen": pollen, "start": start, "end": end})
    return seasons_now


def status(alerts_found, seasons_now):
    """Traffic light for the alert bar: red = in season or pollen forecast, yellow = season within
    WARN_DAYS, green = neither. The most serious one wins."""
    if seasons_now or any(a["kind"] == "forecast" for a in alerts_found):
        return "red"
    if alerts_found:
        return "yellow"
    return "green"


def forecast_alerts(city):
    """Pollen types forecast at or above SYMPTOM_LEVEL for PERSISTENCE_HOURS hours in a row (live API).
    Returns [] when the API cannot be reached."""
    live = live_pollen(city)
    if live is None:
        return []
    current, hourly, _ = live
    future = hourly[hourly["time"] >= pd.Timestamp(current["time"])].reset_index(drop=True)
    alerts = []
    for pollen in POLLEN:
        values = future[f"{pollen.lower()}_pollen"].fillna(0)
        in_a_row = (values >= SYMPTOM_LEVEL).astype(int).rolling(PERSISTENCE_HOURS).sum() == PERSISTENCE_HOURS
        if in_a_row.any():
            first_hour = future.loc[in_a_row.idxmax() - PERSISTENCE_HOURS + 1, "time"]
            alerts.append({"kind": "forecast", "city": city, "pollen": pollen, "from": first_hour,
                           "peak": values.max()})
    return sorted(alerts, key=lambda a: a["from"])


def check(city, today=None, use_forecast=True):
    """All alerts for a city. `today` can be set to another date to test (e.g. 2 April);
    the live forecast only makes sense for the real today, so it is skipped then."""
    real_today = pd.Timestamp.now(tz="Europe/Stockholm").date()
    today = today or real_today
    alerts = coming_alerts(city, today)
    if use_forecast and today == real_today:
        alerts += forecast_alerts(city)
    return alerts


def _when(days):
    """1 → 'tomorrow', 5 → 'in about 5 days', 8 → 'in about 1 week', 13 → 'in about 2 weeks'."""
    if days == 1:
        return "tomorrow"
    if days < 7:
        return f"in about {days} days"
    weeks = round(days / 7)
    return f"in about {weeks} week{'s' if weeks > 1 else ''}"


def message(alert):
    """(title, text) for a notification or the alert bar."""
    icon, pollen, city = ICONS[alert["pollen"]], alert["pollen"], alert["city"]
    if alert["kind"] == "coming":
        return (f"{icon} {pollen} pollen {_when(alert['days'])} in {city}",
                f"The {pollen.lower()} season usually starts around {alert['start']:%d %b} "
                f"(earliest year: {alert['earliest']:%d %b}).")
    return (f"⚠️ {pollen} pollen forecast in {city}",
            f"Above {SYMPTOM_LEVEL} grains/m³ from {alert['from']:%a %d %b %H:00} "
            f"(up to {alert['peak']:.0f}). Symptoms are likely for sensitive people.")


def short_message(alert):
    """Compact one-line version for the dashboard alert bar (the bar's heading already names the city and date):
    '🌳 Birch in about 2 weeks · usually 16 Apr (between 3 and 27 Apr in 2021–2026)'."""
    icon, pollen = ICONS[alert["pollen"]], alert["pollen"]
    day = lambda d: f"{d.day} {d:%b}"
    if alert["kind"] == "coming":
        first, last = alert["earliest"], alert["latest"]
        span = f"{first.day} and {day(last)}" if first.month == last.month else f"{day(first)} and {day(last)}"
        return f"{icon} {pollen} {_when(alert['days'])} · usually {day(alert['start'])} (between {span} in {alert['years']})"
    return f"⚠️ {pollen} above {SYMPTOM_LEVEL} grains/m³ from {alert['from']:%a %H:00} (up to {alert['peak']:.0f})"


def next_season(city, today):
    """(pollen, date) of the next typical season start after `today` – used when there is no alert."""
    typical = typical_seasons().query("city == @city").set_index("pollen_type")["start_doy"]
    starts = []
    for pollen, doy in typical.items():
        start = _doy_to_date(doy, today.year)
        starts.append((start if start > today else _doy_to_date(doy, today.year + 1), pollen))
    start, pollen = min(starts)
    return pollen, start
