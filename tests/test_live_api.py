"""Tests for the live Open-Meteo call in dashboard/data.py (live_pollen) and the week chart for today.

The API is replaced by a mock (FakeResponse / patch), so the tests run without internet, in under a second,
and always give the same result. Three situations are checked:
1. API OK    – the JSON becomes the right current values and hourly table
2. API down  – no internet, timeout or server error → None (no crash) and the chart shows a warning
3. Cache     – same city within 15 min → no new API call; other city or after 15 min → new call

Run:  uv run pytest
"""
import time
from unittest.mock import patch

import pandas as pd
import pytest
import requests

import charts
import data


class FakeResponse:
    """Imitates requests.Response: only what live_pollen() uses."""

    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")

    def json(self):
        return self._json_data


# Same shape as the real answer, with values we chose (birch 42 now) so the expected result is known
FAKE_JSON = {
    "current": {"time": "2026-05-01T10:00", "alder_pollen": 0.0, "birch_pollen": 42.0,
                "grass_pollen": 0.0, "mugwort_pollen": 0.0},
    "hourly": {
        "time": ["2026-05-01T09:00", "2026-05-01T10:00", "2026-05-01T11:00"],
        "alder_pollen": [0.0, 0.0, 0.0],
        "birch_pollen": [30.0, 42.0, 55.0],
        "grass_pollen": [0.0, 0.0, 0.0],
        "mugwort_pollen": [0.0, 0.0, 0.0],
    },
}


@pytest.fixture(autouse=True)
def empty_cache():
    """Every test starts with an empty cache, so earlier tests cannot affect it."""
    data._live_cache.clear()
    yield
    data._live_cache.clear()


# ---------------------------------------------------------------- 1. API OK
def test_api_ok_returns_current_values_and_hourly_table():
    with patch("data.requests.get", return_value=FakeResponse(FAKE_JSON)):
        current, hourly, fetched_at = data.live_pollen("Stockholm")

    assert current["birch_pollen"] == 42
    assert len(hourly) == 3
    assert hourly["time"].dtype.kind == "M"  # datetime, so the charts can use it as a time axis
    assert hourly["birch_pollen"].tolist() == [30.0, 42.0, 55.0]
    assert fetched_at.tz is not None          # Swedish time, shown as "updated HH:MM"


# ---------------------------------------------------------------- 2. API down
@pytest.mark.parametrize("behaviour", [
    {"side_effect": requests.ConnectionError("no internet")},
    {"side_effect": requests.Timeout("too slow")},
    {"return_value": FakeResponse({}, status_code=500)},
], ids=["no internet", "timeout", "server error 500"])
def test_api_down_returns_none(behaviour):
    with patch("data.requests.get", **behaviour):
        assert data.live_pollen("Stockholm") is None


def test_api_down_chart_shows_warning():
    with patch("data.requests.get", side_effect=requests.ConnectionError("no internet")):
        fig = charts.week_chart("Stockholm")

    assert "unavailable" in fig.layout.annotations[0].text


# ---------------------------------------------------------------- pollen release time (model metadata)
@pytest.mark.parametrize("published_utc, expected", [
    ("2026-07-07 11:34", "13:30"),   # summer: Swedish time = UTC + 2
    ("2026-01-07 11:34", "12:30"),   # winter: Swedish time = UTC + 1
])
def test_pollen_release_time_in_swedish_time(published_utc, expected):
    data._release_cache.clear()
    meta = {"last_run_availability_time": pd.Timestamp(published_utc, tz="UTC").timestamp()}
    with patch("data.requests.get", return_value=FakeResponse(meta)):
        assert data.pollen_release_time() == expected
    data._release_cache.clear()


# ---------------------------------------------------------------- 3. Cache
def test_cache_saves_calls_and_expires_after_15_minutes():
    with patch("data.requests.get", return_value=FakeResponse(FAKE_JSON)) as fake_get:
        data.live_pollen("Stockholm")
        assert fake_get.call_count == 1

        data.live_pollen("Stockholm")                 # same city right away → from the cache
        assert fake_get.call_count == 1

        data.live_pollen("Luleå")                     # other city → not in the cache
        assert fake_get.call_count == 2

        with patch("data.time.time", return_value=time.time() + 16 * 60):
            data.live_pollen("Stockholm")             # 16 min later → cache expired
        assert fake_get.call_count == 3
