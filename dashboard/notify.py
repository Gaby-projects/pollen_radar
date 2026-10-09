"""Pollen alerts as notifications, for one or all cities: a Windows pop-up and/or a phone push via ntfy.

Usage:
    uv run python dashboard/notify.py --city Stockholm                       # real today (season + live forecast)
    uv run python dashboard/notify.py --city Stockholm --date 2026-04-02     # test: pretend it is 2 April
    uv run python dashboard/notify.py --city all --channel ntfy              # phones subscribed in the ntfy app
    uv run python dashboard/notify.py --city all --channel both --dry-run    # only print, nothing sent

Channels:
    windows – pop-up on this computer (winotify)
    ntfy    – push to the ntfy app: one channel for all cities, pollen-project-gab (see alerts.ntfy_topic)
    both    – both of the above

Run daily with Windows Task Scheduler (later: GitHub Actions). Each alert is sent once per channel: sent
alerts are remembered in logs/alerts_sent.json (except in test mode with --date, which always sends them).
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import requests

from alerts import NTFY_SERVER, NTFY_TAGS, check, message, next_season, ntfy_topic
from data import CITIES

ROOT = Path(__file__).resolve().parents[1]
SENT_LOG = ROOT / "logs" / "alerts_sent.json"
ICON = ROOT / "dashboard" / "assets" / "img" / "birch_flower.jpg"
CHANNELS = {"windows": ["windows"], "ntfy": ["ntfy"], "both": ["windows", "ntfy"]}


def alert_key(alert, channel):
    """'coming' alerts once per season, 'forecast' alerts once per day – per channel, so sending to ntfy
    later still works after a Windows pop-up was shown."""
    if alert["kind"] == "coming":
        return f"{channel}|{alert['city']}|{alert['pollen']}|coming|{alert['start'].year}"
    return f"{channel}|{alert['city']}|{alert['pollen']}|forecast|{alert['from']:%Y-%m-%d}"


def load_sent():
    return set(json.loads(SENT_LOG.read_text(encoding="utf-8"))) if SENT_LOG.exists() else set()


def save_sent(sent):
    SENT_LOG.parent.mkdir(exist_ok=True)
    SENT_LOG.write_text(json.dumps(sorted(sent), indent=2, ensure_ascii=False), encoding="utf-8")


def show_toast(title, text):
    """Windows notification; on other systems (or without winotify) just print it."""
    try:
        from winotify import Notification
    except ImportError:
        print(f"[notification] {title} – {text}")
        return
    Notification(app_id="Pollen Radar Sweden", title=title, msg=text,
                 icon=str(ICON) if ICON.exists() else "").show()


def send_ntfy(alert, title, text):
    """Push an alert (from alerts.check) to the ntfy channel. Returns True if ntfy accepted it."""
    return send_ntfy_message(alert["pollen"], alert["kind"], title, text)


def send_ntfy_message(pollen, kind, title, text):
    """Push one message to the ntfy channel (all cities; the title names the city). The emoji comes from the
    tag (shown by the app), so it is removed from the title; forecast alerts (pollen in the next days) get high
    priority. Returns True if ntfy accepted it."""
    headers = {"Title": title.split(" ", 1)[1], "Tags": NTFY_TAGS[pollen],
               "Priority": "high" if kind == "forecast" else "default"}
    try:
        r = requests.post(f"{NTFY_SERVER}/{ntfy_topic()}", data=text.encode("utf-8"), headers=headers, timeout=10)
        return r.ok
    except requests.RequestException:
        return False


def main():
    parser = argparse.ArgumentParser(description="Pollen alerts as Windows and/or ntfy notifications")
    parser.add_argument("--city", default="Stockholm", help=f"one of {', '.join(CITIES)}, or 'all'")
    parser.add_argument("--date", type=dt.date.fromisoformat, help="test date, e.g. 2026-04-02")
    parser.add_argument("--channel", choices=CHANNELS, default="windows", help="where to send (default: windows)")
    parser.add_argument("--dry-run", action="store_true", help="only print the alerts, send nothing")
    args = parser.parse_args()

    cities = CITIES if args.city == "all" else [args.city]
    if not set(cities) <= set(CITIES):
        sys.exit(f"Unknown city '{args.city}'. Use one of: {', '.join(CITIES)} or 'all'.")

    sent = load_sent()
    for city in cities:
        alerts = check(city, today=args.date)
        if not alerts:
            pollen, start = next_season(city, args.date or dt.date.today())
            print(f"{city}: no alerts – next season: {pollen.lower()}, around {start:%d %b %Y}")
        for alert in alerts:
            title, text = message(alert)
            for channel in CHANNELS[args.channel]:
                key = alert_key(alert, channel)
                if args.date is None and key in sent:
                    print(f"{city} [{channel}]: already sent – {title}")
                    continue
                print(f"{city} [{channel}]: {title} – {text}")
                if args.dry_run:
                    continue
                if channel == "windows":
                    show_toast(title, text)
                    ok = True
                else:
                    ok = send_ntfy(alert, title, text)
                    print(f"   → ntfy channel {ntfy_topic(city)}: {'sent' if ok else 'FAILED (not sent)'}")
                if ok and args.date is None:
                    sent.add(key)
    save_sent(sent)


if __name__ == "__main__":
    main()
