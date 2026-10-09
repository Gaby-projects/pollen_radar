"""Tests for the pollen alert logic (dashboard/alerts.py).

Season dates come from the data (DuckDB or the Parquet snapshot); the live forecast is replaced by
fake data, so no internet is needed. Typical Stockholm starts used below: alder ~8 Mar, birch ~16 Apr.

Run:  uv run pytest
"""
import datetime as dt
from unittest.mock import patch

import pandas as pd

import alerts


def fake_live(birch_values):
    """Fake live_pollen() result: hourly birch values from 10:00 today, other types 0."""
    times = pd.date_range("2026-05-01 10:00", periods=len(birch_values), freq="h")
    hourly = pd.DataFrame({"time": times, "alder_pollen": 0.0, "birch_pollen": birch_values,
                           "grass_pollen": 0.0, "mugwort_pollen": 0.0})
    current = {"time": "2026-05-01T10:00"}
    return current, hourly, pd.Timestamp("2026-05-01 10:05", tz="Europe/Stockholm")


# ---------------------------------------------------------------- "coming" alerts (season within 14 days)
def test_birch_coming_in_two_weeks():
    found = alerts.coming_alerts("Stockholm", dt.date(2026, 4, 2))
    assert [a["pollen"] for a in found] == ["Birch"]
    assert found[0]["days"] == 14
    title, text = alerts.message(found[0])
    assert title == "🌳 Birch pollen in about 2 weeks in Stockholm"
    assert "16 Apr" in text


def test_no_alert_when_season_is_further_than_14_days():
    assert alerts.coming_alerts("Stockholm", dt.date(2026, 1, 15)) == []   # alder ~8 Mar: 52 days away


def test_no_alert_once_the_season_has_started():
    assert alerts.coming_alerts("Stockholm", dt.date(2026, 4, 20)) == []   # birch started ~16 Apr


def test_next_season_wraps_to_next_year():
    pollen, start = alerts.next_season("Stockholm", dt.date(2026, 10, 7))
    assert pollen == "Alder"
    assert start.year == 2027


# ---------------------------------------------------------------- traffic light (alert bar colour)
def test_traffic_light_green_yellow_red():
    def colour(day):
        today = dt.date(*day)
        return alerts.status(alerts.check("Stockholm", today=today), alerts.in_season("Stockholm", today))

    assert colour((2026, 10, 7)) == "green"    # October: no season now or within 14 days
    assert colour((2027, 2, 25)) == "yellow"   # alder starts ~8 Mar: 11 days away
    assert colour((2026, 5, 1)) == "red"       # inside the birch season


def test_forecast_alone_makes_it_red():
    forecast = [{"kind": "forecast"}]
    assert alerts.status(forecast, seasons_now=[]) == "red"


def test_alert_bar_for_a_past_date_is_compact():
    import app  # dashboard/app.py

    _title, bar, _photos = app.update_alert("Stockholm", "2025-04-02", None)   # date picker value
    header, alert_line = (c.children for c in bar.children if c is not None)
    assert alert_line == "🌳 Birch in about 2 weeks · usually 16 Apr (between 3 and 27 Apr in 2021–2026)"   # short version
    assert bar.children[-1] is None                                  # no extra 'real data' line for past dates


def test_alert_bar_for_a_future_date_says_it_is_not_a_forecast():
    import app  # dashboard/app.py

    _title, bar, _photos = app.update_alert("Stockholm", "2027-02-25", None)
    assert bar.children[-1].children == "📅 Typical season dates 2021–2026, not a forecast"


def test_photos_highlight_active_pollen_types():
    import app  # dashboard/app.py

    _title, _bar, photos = app.update_alert("Stockholm", "2026-05-01", None)   # birch season
    classes = {card.children[0].children[3].children[0].children: card.className for card in photos}
    assert classes["Birch"] == "photo-card selected"
    assert classes["Grass"] == "photo-card"

    _title, _bar, photos = app.update_alert("Stockholm", "2026-10-07", None)   # nothing active
    assert {card.className for card in photos} == {"photo-card"}       # all in original colours, no border


# ---------------------------------------------------------------- charts follow the selected date
def fake_live_around_today():
    """Fake live_pollen(): hourly values from 2 days ago to 3 days ahead (like the real API), birch 20."""
    today = pd.Timestamp.now(tz="Europe/Stockholm").normalize().tz_localize(None)
    times = pd.date_range(today - pd.Timedelta(days=2), today + pd.Timedelta(days=4), freq="h", inclusive="left")
    hourly = pd.DataFrame({"time": times, "alder_pollen": 0.0, "birch_pollen": 20.0,
                           "grass_pollen": 0.0, "mugwort_pollen": 0.0})
    current = {"time": f"{today:%Y-%m-%d}T10:00", "alder_pollen": 0.0, "birch_pollen": 20.0,
               "grass_pollen": 0.0, "mugwort_pollen": 0.0}
    return current, hourly, pd.Timestamp.now(tz="Europe/Stockholm")


def chart_titles(day):
    import app  # dashboard/app.py

    heading, week, day_fig = app.update_live("Stockholm", day, None)
    return heading, week.layout.title.text, day_fig.layout.title.text


def test_only_today_is_called_live():
    with patch("data.live_pollen", return_value=fake_live_around_today()):
        heading, week, day = chart_titles(None)                       # today
    assert heading.startswith("📡 Live pollen information for today")
    assert week.startswith("<b>Live this week") and day.startswith("<b>Live today")


def test_past_date_uses_historical_data():
    heading, week, day = chart_titles("2025-04-02")
    assert heading == "📊 Pollen information for Wednesday 02 April 2025 – historical data"
    assert "Live" not in week + day
    assert "birch peaks at" in day and "historical data" in day


def test_next_days_use_the_api_forecast():
    in_two_days = (pd.Timestamp.now(tz="Europe/Stockholm") + pd.Timedelta(days=2)).date().isoformat()
    with patch("data.live_pollen", return_value=fake_live_around_today()):
        heading, week, day = chart_titles(in_two_days)
    assert heading.startswith("🔮 Pollen forecast for")
    assert "Live" not in week + day and "Forecast for Stockholm" in day


def test_far_future_uses_typical_values():
    with patch("data.live_pollen", return_value=None):
        heading, week, day = chart_titles("2027-05-01")
    assert heading == "📅 Typical pollen for Saturday 01 May – average of the same dates 2021–2026, not a forecast"
    assert "Live" not in week + day and "Typical day in Stockholm" in day


# ---------------------------------------------------------------- "forecast" alerts (live, persistence)
def test_forecast_alert_after_3_hours_in_a_row():
    with patch("alerts.live_pollen", return_value=fake_live([2, 12, 15, 18, 20])):
        found = alerts.forecast_alerts("Stockholm")
    assert len(found) == 1
    assert found[0]["pollen"] == "Birch"
    assert found[0]["from"] == pd.Timestamp("2026-05-01 11:00")   # first hour of the 3-hour run
    assert found[0]["peak"] == 20


def test_no_forecast_alert_for_a_short_peak():
    # above 10 for only 2 hours in a row: could be noise, no alert
    with patch("alerts.live_pollen", return_value=fake_live([2, 12, 15, 3, 25, 1])):
        assert alerts.forecast_alerts("Stockholm") == []


def test_no_forecast_alert_when_api_is_down():
    with patch("alerts.live_pollen", return_value=None):
        assert alerts.forecast_alerts("Stockholm") == []


def test_test_date_skips_the_live_forecast():
    # with a test date the forecast (which is always for the real today) must not be used
    with patch("alerts.live_pollen") as fake:
        alerts.check("Stockholm", today=dt.date(2026, 4, 2))
    fake.assert_not_called()
