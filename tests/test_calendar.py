"""Tests for the Pollen calendar tab: 'All cities' compares the six cities, one city shows only that city.

Run:  uv run pytest
"""
import app  # dashboard/app.py
from data import CITIES


def test_all_cities_shows_every_city():
    timeline, kpis, heatmap, seasons, hours, risk = app.update_calendar("All cities", "Birch")
    assert list(heatmap.data[0].y) == CITIES
    assert list(seasons.data[0].y) == CITIES
    assert list(risk.data[0].y) == CITIES
    assert "median of 6 cities" in kpis[0].children[1].children
    assert "average of all cities" in hours.layout.title.text


def test_one_city_shows_only_that_city():
    timeline, kpis, heatmap, seasons, hours, risk = app.update_calendar("Umeå", "Birch")
    years = ["2021", "2022", "2023", "2024", "2025", "2026"]
    assert list(heatmap.data[0].y) == years            # one row per year, not one long thin row
    assert list(risk.data[0].y) == years
    assert list(seasons.data[0].y) == years            # one bar per year
    assert "in Umeå" in heatmap.layout.title.text and "in Umeå" in risk.layout.title.text
    assert "Pollen season in Umeå" in timeline.layout.title.text
    assert "Umeå" in hours.layout.title.text
