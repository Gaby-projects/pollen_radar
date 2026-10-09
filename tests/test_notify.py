"""Tests for the notifications (dashboard/notify.py): one ntfy channel for all cities, what is sent to ntfy, and
the 'already sent' memory per channel. ntfy itself is faked, so nothing reaches a phone.

Run:  uv run pytest
"""
import datetime as dt
from unittest.mock import patch

import alerts
import notify


def test_one_ntfy_channel_for_all_cities():
    assert alerts.ntfy_topic("Stockholm") == alerts.ntfy_topic("Luleå") == alerts.NTFY_TOPIC == "pollen-project-gab"


def test_send_ntfy_posts_to_the_channel():
    alert = alerts.check("Göteborg", today=dt.date(2026, 5, 25))[0]          # grass in ~2 weeks
    title, text = alerts.message(alert)
    with patch("notify.requests.post") as post:
        post.return_value.ok = True
        assert notify.send_ntfy(alert, title, text)
    url, kwargs = post.call_args.args[0], post.call_args.kwargs
    assert url == f"{alerts.NTFY_SERVER}/{alerts.NTFY_TOPIC}"
    assert kwargs["headers"]["Title"] == "Grass pollen in about 2 weeks in Göteborg"   # emoji comes from the tag
    assert kwargs["headers"]["Tags"] == "ear_of_rice"
    assert kwargs["headers"]["Priority"] == "default"                                # 'coming' alert
    assert kwargs["data"].decode("utf-8") == text


def test_send_ntfy_reports_failure_without_crashing():
    alert = alerts.check("Göteborg", today=dt.date(2026, 5, 25))[0]
    with patch("notify.requests.post", side_effect=notify.requests.ConnectionError("no internet")):
        assert notify.send_ntfy(alert, *alerts.message(alert)) is False


def test_dashboard_box_shows_the_city_channel():
    import app  # dashboard/app.py

    box = app.update_subscribe("Göteborg")
    text, qr = box.children
    topic = next(c for c in text.children if getattr(c, "className", None) == "subscribe-topic")
    assert topic.children == alerts.ntfy_topic("Göteborg")          # same channel as notify.py sends to
    assert qr.children[0].src.startswith("data:image/svg+xml;base64,")   # QR code image of the channel link


def test_send_button_is_off_without_an_alert_and_on_with_one():
    import app  # dashboard/app.py

    disabled, _, _ = app.update_send_button("Stockholm", "2026-10-07")     # October: nothing to send
    assert disabled
    disabled, title, _ = app.update_send_button("Stockholm", "2026-04-02")  # birch in ~2 weeks
    assert not disabled and alerts.ntfy_topic("Stockholm") in title


def test_send_button_sends_the_alert_to_the_channel():
    import app  # dashboard/app.py

    with patch("notify.requests.post") as post:
        post.return_value.ok = True
        status = app.press_send(1, "Stockholm", "2026-04-02")
    assert post.call_args.args[0].endswith(alerts.ntfy_topic("Stockholm"))
    assert status.children.startswith("✅ Sent 1 alert to")

    with patch("notify.requests.post", side_effect=notify.requests.ConnectionError("no internet")):
        status = app.press_send(1, "Stockholm", "2026-04-02")
    assert status.children.startswith("❌ Could not reach ntfy")


def test_already_sent_is_remembered_per_channel():
    alert = alerts.check("Göteborg", today=dt.date(2026, 5, 25))[0]
    assert notify.alert_key(alert, "windows") != notify.alert_key(alert, "ntfy")
