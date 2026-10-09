"""Tests for the 'Update data' button (dashboard/update.py). The three pipeline steps are faked with a mock,
so nothing is downloaded or rebuilt.

Run:  uv run pytest
"""
import subprocess
from unittest.mock import patch

import data
import update


def test_days_behind():
    import datetime as dt
    today = dt.date(2026, 10, 8)
    assert update.days_behind("2026-10-07", today) == 0     # up to yesterday = up to date
    assert update.days_behind("2026-10-05", today) == 2
    assert update.days_behind("2026-10-08", today) == 0     # never negative


def test_button_is_disabled_when_data_is_up_to_date():
    import app  # dashboard/app.py

    with patch("update.days_behind", return_value=0):
        info, button, _ = app.update_box().children
    assert button.disabled and button.children == "🔄 Update data"   # status only in the text, not twice
    assert "✅ Dashboard up to date · Next update:" in info.children[1].children

    with patch("update.days_behind", return_value=2):
        info, button, _ = app.update_box().children
    assert not button.disabled and button.children == "🔄 Update data"
    assert "⚠️ Update needed (2 days missing)" in info.children[1].children


def fake_step(returncode, output="done"):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=output, stderr="")


def test_all_steps_ok_runs_three_steps_and_clears_the_caches():
    data.typical_seasons()                                   # fill one cache
    assert data.typical_seasons.cache_info().currsize == 1
    with patch("update.subprocess.run", return_value=fake_step(0)) as run:
        ok, results = update.run_update()
    assert ok
    assert run.call_count == 3
    assert [name for name, _, _ in results] == [name for name, _, _ in update.STEPS]
    assert data.typical_seasons.cache_info().currsize == 0  # new data will be read


def test_stops_at_the_first_failing_step():
    steps = [fake_step(0), fake_step(1, "Done. PASS=57 ERROR=1")]    # ingest ok, dbt fails
    with patch("update.subprocess.run", side_effect=steps) as run:
        ok, results = update.run_update()
    assert not ok
    assert run.call_count == 2                                   # the snapshot step is not run
    name, step_ok, output = results[-1]
    assert name == "Rebuild and test tables (dbt build)" and not step_ok and "ERROR=1" in output[-1]


def test_timeout_is_reported_as_a_failure():
    with patch("update.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ingest", timeout=1)):
        ok, results = update.run_update()
    assert not ok and "stopped after" in results[0][2][0]
