"""Pollen Radar Sweden – Dash dashboard.

Run locally:  uv run python dashboard/app.py   ->   open http://127.0.0.1:8050
Production (Render):  gunicorn --chdir dashboard app:server
"""
import base64
import datetime as dt

import pandas as pd
import qrcode
import qrcode.image.svg
from dash import Dash, Input, Output, State, dcc, html, no_update

import alerts
import charts
import notify
import update
from data import (ALL_CITIES, CITIES, HIGH_THRESHOLD, KPIS, PLANT_PHOTOS, POLLEN, SOURCES, daily,
                  data_coverage, event_risk, hourly_profile, pollen_for_date, pollen_release_time, rain_events, retail_need, risk_days,
                  season_days,
                  start_gaps, stock_plan, tourism, typical_seasons)

# compress=False: with compression the local server cut the 4.8 MB plotly.js download
# ("connection reset") and no chart was drawn
app = Dash(__name__, title="Pollen Radar Sweden", compress=False)
server = app.server  # the Flask app inside Dash: what gunicorn runs in production


# ------------------------------- building blocks -------------------------------
def kpi_card(value, label):
    return html.Div(className="kpi", children=[html.Div(value, className="kpi-value"),
                                               html.Div(label, className="kpi-label")])


def graph(figure=None, graph_id=None):
    props = {"config": {"displayModeBar": False}, "className": "card"}
    if graph_id:
        props["id"] = graph_id
    if figure is not None:
        props["figure"] = figure
    return dcc.Graph(**props)


def dropdown(dropdown_id, options, value, label):
    return html.Div(className="filter", children=[
        html.Label(label, htmlFor=dropdown_id),
        dcc.Dropdown(id=dropdown_id, options=options, value=value, clearable=False),
    ])


def footer(extra=None):
    """Sources line + an extra line (text, or a list of text and links)."""
    extra = extra or "Pollen data: CAMS via Open-Meteo (model estimates). Pattern information, not medical advice."
    return html.Footer(className="footer", children=[
        "Sources: ",
        *[item for key in SOURCES for item in (html.A(key, href=SOURCES[key][1], target="_blank",
                                                      title=SOURCES[key][0]), " · ")][:-1],
        html.Br(),
        *(extra if isinstance(extra, list) else [extra]),
    ])


# ------------------------------- tab: Why this matters -------------------------------
def why_this_matters():
    cov = data_coverage()
    period = f"{cov['first_day']:%Y}–{cov['last_day']:%Y}"
    return html.Div(className="tab-body", children=[
        html.Div(className="kpi-row", children=[kpi_card(k["value"], k["label"]) for k in KPIS]),
        html.Div(className="grid-2", children=[graph(charts.prevalence_chart()), graph(charts.season_change_chart())]),
        html.H3("What this dashboard adds", className="section-title"),
        html.Div(className="kpi-row", children=[
            kpi_card(str(cov["n_cities"]), "cities, Malmö → Luleå"),
            kpi_card("24 h", "hourly data"),
            kpi_card(str(cov["n_pollen"]), "pollen types + weather + air quality"),
            kpi_card(period, f"data up to {cov['last_day']:%d %b %Y}"),
        ]),
        footer(),
    ])


# ------------------------------- tab: Pollen now -------------------------------
def photo_cards(active):
    """One card per pollen type: whole plant + flowers, name in English and Swedish, plant type.
    All cards keep their original colours; pollen types in `active` (in season or with an alert) get a
    blue border."""
    def card_class(p):
        return "photo-card selected" if p in active else "photo-card"

    return [
        html.Div(className=card_class(p), children=[
            html.Div(className="photo-img", children=[
                html.Img(src=app.get_asset_url(info["plant"]["file"]), alt=f"{p} – whole plant"),
                html.Img(src=app.get_asset_url(info["flower"]["file"]), alt=f"{p} – flowers that release the pollen"),
                html.Span(info["type_en"], className="photo-type"),
                # name on the photos: English + Swedish
                html.Div(className="photo-label", children=[
                    html.Span(p, className="photo-name"),
                    html.Span(info["swedish"].capitalize(), className="photo-swedish"),
                ]),
            ]),
            html.Div(className="photo-sub", children=[html.Span("plant | flowers"), html.Span(info["months"])]),
        ])
        for p, info in PLANT_PHOTOS.items()
    ]


def photo_credits():
    credits = []
    for p, info in PLANT_PHOTOS.items():
        credits += [f"{p} ", html.A("plant", href=info["plant"]["url"], target="_blank"), " / ",
                    html.A("flowers", href=info["flower"]["url"], target="_blank"), " · "]
    return ["Photos: Wikimedia Commons, AnRo0002 (CC0); birch catkins DimiTalen (CC BY-SA 3.0) – ", *credits[:-1]]


def pollen_now():
    """Plant photos, the alert bar (traffic light) and two pollen charts for the selected city and date.
    Today the charts are live (Open-Meteo API); other dates use history, the forecast or typical values."""
    return html.Div(className="tab-body", children=[
        html.Div(id="now-photos", className="photo-row"),
        html.Div(className="filter-row", children=[
            dropdown("now-city", CITIES, "Stockholm", "City"),
            # Pick another day to see the alert and the pollen for that date (empty = today).
            # Past days (2021 → today) also show what really happened, to compare the alert with reality.
            html.Div(className="filter", children=[
                html.Label("Date (empty = today)", htmlFor="now-date"),
                dcc.DatePickerSingle(id="now-date", placeholder="Today", clearable=True, first_day_of_week=1,
                                     display_format="D MMM YYYY", min_date_allowed=dt.date(2021, 1, 1),
                                     max_date_allowed=dt.date(2027, 12, 31)),
            ]),
        ]),
        html.H3(id="now-alert-title", className="section-title"),  # names the city and date of the alert
        html.Div(id="now-alert"),  # pollen alerts for the selected city and date (same logic as notify.py)
        html.Div(id="now-subscribe"),  # how to get these alerts on a phone (ntfy channel of the selected city)
        # Demo button: send the alerts of the selected city and date to the phones subscribed to that city's channel.
        # Local only (hidden on Render, so nobody else can post to the channels); kept in the layout for the callback
        html.Div(className="send-row", style=None if update.can_update() else {"display": "none"}, children=[
            html.Button("📤 Send this alert to phones", id="now-send-btn", className="send-btn", n_clicks=0),
            dcc.Loading(html.Span(id="now-send-status", className="send-status"), type="dot"),
        ]),
        # Heading that says which date the charts show and where the data comes from ('live' only for today)
        html.H3(id="now-live-title", className="section-title"),
        # Week around the selected date (left) and the selected date hour by hour (right)
        html.Div(className="grid-2", children=[graph(graph_id="now-week"), graph(graph_id="now-day")]),
        dcc.Interval(id="live-refresh", interval=60 * 60 * 1000),  # refresh every hour (live data)
        footer(["Pollen: CAMS model via the Open-Meteo API (live and forecast) and the project database (history). "
                "Pattern information, not medical advice.", html.Br(), *photo_credits()]),
    ])


# ------------------------------- tab: Pollen calendar -------------------------------
def pollen_calendar():
    """Typical seasons. 'All cities' compares the six cities; one city shows only that city."""
    return html.Div(className="tab-body", children=[
        html.Div("Pollen doesn't follow the calendar. Now you can follow the pollen.", className="pitch"),
        html.Div(className="filter-row", children=[
            dropdown("cal-city", [ALL_CITIES] + CITIES, ALL_CITIES, "City"),
            dropdown("cal-pollen", POLLEN, "Birch", "Pollen type"),
        ]),
        graph(graph_id="cal-timeline"),
        html.Div(id="cal-kpis", className="kpi-row"),
        html.Div(className="grid-2", children=[graph(graph_id="cal-heatmap"), graph(graph_id="cal-seasons")]),
        html.Div(className="grid-2", children=[graph(graph_id="cal-hours"), graph(graph_id="cal-risk")]),
        footer("Alder and mugwort are weak in the pollen model (CAMS). Pattern information, not medical advice."),
    ])


@app.callback(
    Output("cal-timeline", "figure"),
    Output("cal-kpis", "children"), Output("cal-heatmap", "figure"), Output("cal-seasons", "figure"),
    Output("cal-hours", "figure"), Output("cal-risk", "figure"),
    Input("cal-city", "value"), Input("cal-pollen", "value"),
)
def update_calendar(city, pollen):
    """All cities: KPIs are the median (dates) or average (hour profile, days) of the six cities."""
    cities = CITIES if city == ALL_CITIES else [city]
    seasons_typical = typical_seasons().query("city in @cities and pollen_type == @pollen")
    hours = (hourly_profile().query("city in @cities and pollen_type == @pollen")
             .groupby("hour_local")["index"].mean())
    d = daily().query("city in @cities")
    high_days = d[f"high_{pollen}"].sum() / d["year"].nunique() / len(cities)
    where = " (median of 6 cities)" if city == ALL_CITIES else ""
    kpis = [
        kpi_card(charts.doy_to_text(seasons_typical["start_doy"].median()), f"typical {pollen.lower()} season start{where}"),
        kpi_card(charts.doy_to_text(seasons_typical["peak_doy"].median()), f"typical peak day{where}"),
        kpi_card(f"{int(hours.idxmin()):02d}:00", "cleanest hour of the day"),
        kpi_card(f"{high_days:.0f}", f"high-pollen days per year (> {HIGH_THRESHOLD[pollen]} grains/m³)"
                 + (", per city" if city == ALL_CITIES else "")),
    ]
    return (charts.pollen_timeline(city), kpis, charts.calendar_heatmap(pollen, city),
            charts.season_bars(pollen, city), charts.hour_profile(city, pollen), charts.risk_calendar_chart(city))


# ------------------------------- tab: Pollen now – alert bar and live callbacks -------------------------------
def alert_bar(city, today=None):
    """Compact traffic-light alert bar for the selected city (same rules as the notifications):
    🔴 red = inside a typical pollen season or pollen forecast ≥ 10 grains/m³ · 🟡 yellow = a season starts
    within 14 days · 🟢 green = no season now or soon. The heading above already names the city and date, and
    the page header shows how recent the data is, so the bar only says what matters for that day.
    `today` = another date (date picker)."""
    real_today = pd.Timestamp.now(tz="Europe/Stockholm").date()
    today = today or real_today
    found = alerts.check(city, today=today)
    seasons_now = alerts.in_season(city, today)
    colour = alerts.status(found, seasons_now)
    day = lambda d: f"{d.day} {d:%b}"
    if colour == "green":
        pollen, start = alerts.next_season(city, today)
        header = f"🟢 No pollen season · next: {pollen.lower()}, around {day(start)}"
    elif colour == "yellow":
        header = "🟡 Pollen season coming soon"
    elif seasons_now:
        header = "🔴 Pollen season: " + ", ".join(
            f"{s['pollen'].lower()} ({day(s['start'])} – {day(s['end'])})" for s in seasons_now)
    else:
        header = "🔴 Pollen forecast"
    lines = [html.Div(alerts.short_message(a), className="alert-line") for a in found]
    if today > real_today:
        # The live forecast only covers the next 4 days, so future dates use the typical dates (climatology)
        note = html.Div("📅 Typical season dates 2021–2026, not a forecast", className="alert-note")
    else:
        note = None
    bar = html.Div(className=f"alert-bar {colour}", children=[html.Div(html.B(header)), *lines, note])
    active = {s["pollen"] for s in seasons_now} | {a["pollen"] for a in found}
    return bar, active


def _selected_day(picked):
    """Date picker value → date (empty = today, Swedish time)."""
    return dt.date.fromisoformat(picked[:10]) if picked else pd.Timestamp.now(tz="Europe/Stockholm").date()


@app.callback(Output("now-alert-title", "children"), Output("now-alert", "children"), Output("now-photos", "children"),
              Input("now-city", "value"), Input("now-date", "date"), Input("live-refresh", "n_intervals"))
def update_alert(city, picked, _):
    """Heading + alert bar + plant photos for the selected city and date (date picker empty = today); refreshed
    every hour too. The photos highlight the pollen types that are in season or have an alert."""
    real_today = pd.Timestamp.now(tz="Europe/Stockholm").date()
    day = _selected_day(picked)
    when = "today" if day == real_today else "past date" if day < real_today else "future date"
    title = f"🔔 Pollen alert per date – {city}, {day:%A %d %B %Y} ({when})"
    bar, active = alert_bar(city, day)
    return title, bar, photo_cards(active)


def qr_code(url):
    """QR code of a link as an SVG image (sharp at any size, no image library needed), ready for html.Img."""
    svg = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, border=1).to_string()
    return "data:image/svg+xml;base64," + base64.b64encode(svg).decode()


def subscribe_box(city):
    """How to get the alerts on a phone: the free ntfy app + the channel (one for all cities, same name as
    notify.py), with a QR code of the channel's web page (it opens the web version, not the app)."""
    topic = alerts.ntfy_topic(city)
    link = f"{alerts.NTFY_SERVER}/{topic}"
    return html.Div(className="subscribe-box", children=[
        html.Div(className="subscribe-text", children=[
            html.B("📲 Alerts on your phone: "),
            html.A("ntfy app", href="https://ntfy.sh/#subscribe-phone", target="_blank"),
            " → subscribe to ",
            html.Code(topic, className="subscribe-topic"),
            " · ",
            html.A("web", href=link, target="_blank"),
        ]),
        html.Div(className="subscribe-qr", children=[
            html.Img(src=qr_code(link), alt=f"QR code: subscribe to {topic} in ntfy"),
            html.Span("Web version only"),
        ]),
    ])


@app.callback(Output("now-subscribe", "children"), Input("now-city", "value"))
def update_subscribe(city):
    return subscribe_box(city)


@app.callback(Output("now-send-btn", "disabled"), Output("now-send-btn", "title"), Output("now-send-status", "children"),
              Input("now-city", "value"), Input("now-date", "date"))
def update_send_button(city, picked):
    """The send button is only active when the selected city and date have an alert (a season coming within
    14 days, or a pollen forecast); a new choice clears the last 'sent' message."""
    found = alerts.check(city, today=_selected_day(picked))
    if not found:
        return True, "No alert for this city and date – pick another date (e.g. 2 April) to try it", ""
    return False, f"Send {len(found)} alert(s) to everyone subscribed to {alerts.ntfy_topic(city)}", ""


@app.callback(Output("now-send-status", "children", allow_duplicate=True),
              Input("now-send-btn", "n_clicks"), State("now-city", "value"), State("now-date", "date"),
              prevent_initial_call=True)
def press_send(n_clicks, city, picked):
    """Send the alerts shown for the selected city and date to the ntfy channel – same messages as notify.py.
    Always sent (test/demo), even if this alert was sent before."""
    found = alerts.check(city, today=_selected_day(picked))
    if not found:
        return "No alert to send for this date"
    sent = sum(notify.send_ntfy(alert, *alerts.message(alert)) for alert in found)
    topic = alerts.ntfy_topic(city)
    if sent == len(found):
        return html.Span(f"✅ Sent {sent} alert{'s' if sent > 1 else ''} to {topic}", className="send-ok")
    return html.Span(f"❌ Could not reach ntfy ({sent} of {len(found)} sent) – check the internet connection",
                     className="send-error")


# Heading above the two charts, per data source: only today's data is called 'live'
CHART_HEADINGS = {
    "live": "📡 Live pollen information for today – {day:%A %d %B %Y} (Swedish time)",
    "history": "📊 Pollen information for {day:%A %d %B %Y} – historical data",
    "recent": "📊 Pollen information for {day:%A %d %B %Y} – recent data from the Open-Meteo API",
    "forecast": "🔮 Pollen forecast for {day:%A %d %B %Y} – Open-Meteo API",
    "typical": "📅 Typical pollen for {day:%A %d %B} – average of the same dates {years}, not a forecast",
}


@app.callback(Output("now-live-title", "children"), Output("now-week", "figure"), Output("now-day", "figure"),
              Input("now-city", "value"), Input("now-date", "date"), Input("live-refresh", "n_intervals"))
def update_live(city, picked, _):
    """Heading + charts for the selected city and date: the week around the date and the date hour by hour.
    Today they are live (one Open-Meteo API call per city, cached 15 min, refreshed every hour); other dates
    use history, the API forecast or typical values (data.pollen_for_date)."""
    day = _selected_day(picked)
    src = pollen_for_date(city, day)
    kind = src["kind"] if src else "live"   # None = live API unreachable today; the charts show a warning
    years = f"{src['years'][0]}–{src['years'][-1]}" if kind == "typical" and src["years"] else ""
    title = CHART_HEADINGS[kind].format(day=day, years=years)
    return title, charts.week_chart(city, day), charts.day_chart(city, day)


# ------------------------------- tab: Weather & air -------------------------------
def weather_and_air():
    # The pitch is the headline of this tab: weather is what tells you when pollen will hit
    return html.Div(className="tab-body", children=[
        html.Div("Know before you sneeze.", className="pitch"),
        html.Div(className="filter-row", children=[
            dropdown("wx-city", [ALL_CITIES] + CITIES, ALL_CITIES, "City"),
        ]),
        html.Div(id="wx-kpis", className="kpi-row"),
        html.Div(className="grid-3", children=[graph(graph_id="wx-rain"), graph(graph_id="wx-temp"),
                                               graph(graph_id="wx-wind")]),
        html.Div(className="grid-3", children=[graph(graph_id="wx-recovery"), graph(graph_id="wx-risk-year"),
                                               graph(graph_id="wx-risk-month")]),
        footer("Birch, grass and mugwort (alder left out: weak data in the pollen model). "
               "Pattern information, not medical advice."),
    ])


@app.callback(
    Output("wx-kpis", "children"), Output("wx-rain", "figure"), Output("wx-temp", "figure"),
    Output("wx-wind", "figure"), Output("wx-recovery", "figure"), Output("wx-risk-year", "figure"),
    Output("wx-risk-month", "figure"),
    Input("wx-city", "value"),
)
def update_weather(city):
    days = season_days() if city == ALL_CITIES else season_days().query("city == @city")
    rain_effect = days.loc[days["Rain"] == "Rainy", "ratio"].mean() / days.loc[days["Rain"] == "Dry", "ratio"].mean()
    events = rain_events() if city == ALL_CITIES else rain_events().query("city == @city")
    within_2 = (events["recovery_days"] <= 2).mean()
    risk = risk_days() if city == ALL_CITIES else risk_days().query("city == @city")
    n_cities = len(CITIES) if city == ALL_CITIES else 1
    risk_per_year = risk["both"].sum() / risk["year"].nunique() / n_cities
    kpis = [
        kpi_card(f"{rain_effect:.1f}×", "pollen on rainy vs dry days"),
        kpi_card(f"{within_2:.0%}", "of rain events: pollen back within 2 days"),
        kpi_card(f"{risk_per_year:.1f}", "days/year with high pollen + bad air" + (" (per city)" if n_cities > 1 else "")),
    ]
    return (kpis, charts.weather_effect(city, "Rain"), charts.weather_effect(city, "Temperature"),
            charts.weather_effect(city, "Wind"), charts.recovery_curve(city), charts.risk_by_year(city),
            charts.risk_by_month(city))


# ------------------------------- tab: Pharmacies -------------------------------
WEAK_DATA = {"Alder": "⚠ Weak data: alder is near zero in the pollen model outside Göteborg.",
             "Mugwort": "⚠ Weak data: mugwort has low levels and the same dates in every city in the pollen model."}


def pharmacies():
    return html.Div(className="tab-body business", children=[
        html.Div("The right stock, in the right city, in the right week.", className="pitch"),
        html.Div(className="filter-row", children=[
            dropdown("ph-pollen", POLLEN, "Birch", "Pollen type"),
            dropdown("ph-city", [ALL_CITIES] + CITIES, ALL_CITIES, "City"),
        ]),
        html.Div(id="ph-warning", className="warning"),
        html.Div(id="ph-kpis", className="kpi-row"),
        graph(graph_id="ph-planning"),
        html.Div(className="grid-3", children=[graph(graph_id="ph-gap"), graph(graph_id="ph-intensity"),
                                               graph(graph_id="ph-demand")]),
        footer("Stock ready = 1 week before the earliest typical start (10th percentile of 2021–2026). "
               "Pollen data: CAMS (model estimates)."),
    ])


@app.callback(
    Output("ph-warning", "children"), Output("ph-kpis", "children"), Output("ph-planning", "figure"),
    Output("ph-gap", "figure"), Output("ph-intensity", "figure"), Output("ph-demand", "figure"),
    Input("ph-pollen", "value"), Input("ph-city", "value"),
)
def update_pharmacies(pollen, city):
    if city == ALL_CITIES:
        plans = stock_plan().query("pollen_type == @pollen")
        gaps = start_gaps().query("pollen_type == @pollen")
        first = plans.loc[plans["stock_ready_week"].idxmin()]
        kpis = [
            kpi_card(f"week {first['stock_ready_week']}", f"first stock ready ({first['city']})"),
            kpi_card(f"week {plans['typical_peak'].median():.0f}", "typical peak, median of 6 cities"),
            kpi_card(f"{gaps['median'].max():.1f} wk", "start gap south → north"),
            kpi_card(charts.k_format(round(plans["yearly_pollen"].mean())), "pollen per season, city average (grains/m³)"),
        ]
    else:
        plan = stock_plan().query("pollen_type == @pollen and city == @city").iloc[0]
        gap = start_gaps().query("pollen_type == @pollen and city == @city").iloc[0]
        kpis = [
            kpi_card(f"week {plan['stock_ready_week']}", f"stock ready in {city}"),
            kpi_card(f"week {plan['typical_peak']:.0f}", "typical peak (highest demand)"),
            kpi_card(f"{gap['median']:+.1f} wk", "start vs Malmö"),
            kpi_card(charts.k_format(round(plan["yearly_pollen"])), "pollen per season (grains/m³)"),
        ]
    return (WEAK_DATA.get(pollen, ""), kpis, charts.planning_heatmap(pollen, city), charts.gap_chart(pollen, city),
            charts.intensity_heatmap(pollen, city), charts.yearly_pollen_bars(pollen, city))


# ------------------------------- tab: Tourism -------------------------------
def tourism_tab():
    t = tourism()

    def best(period):
        row = t.query("period == @period").sort_values("high_any").iloc[0]
        return kpi_card(row["city"], f"best destination {period} ({row['high_any']:.0%} high-pollen days)")

    return html.Div(className="tab-body business", children=[
        html.Div("Breathe smarter.", className="pitch"),
        html.Div(className="filter-row", children=[dropdown("tour-city", CITIES, "Stockholm", "Highlight city")]),
        html.Div(className="kpi-row", children=[best("Apr 1–15"), best("May 16–end"), best("Jun 1–15")]),
        html.Div(className="grid-2", children=[graph(graph_id="tour-heatmap"), graph(graph_id="tour-spring")]),
        footer(),
    ])


@app.callback(Output("tour-heatmap", "figure"), Output("tour-spring", "figure"), Input("tour-city", "value"))
def update_tourism(city):
    return charts.tourism_heatmap(city), charts.spring_bars(city)


# ------------------------------- tab: Events -------------------------------
def events_tab():
    weekly_problem = event_risk().query("18 <= week <= 35").groupby("week")["problem"].mean()
    worst = event_risk().query("14 <= week <= 35").groupby("week")["problem"].mean()
    return html.Div(className="tab-body business", children=[
        html.Div(className="filter-row", children=[dropdown("ev-city", CITIES, "Stockholm", "Highlight city")]),
        html.Div(className="kpi-row", children=[
            kpi_card(f"week {weekly_problem.idxmin()}", "best week for outdoor events (May–Aug)"),
            kpi_card(f"{weekly_problem.min():.0%}", "problem days that week (average of 6 cities)"),
            kpi_card(f"week {worst.idxmax()}", f"worst week ({worst.max():.0%} problem days)"),
        ]),
        html.Div(className="grid-2", children=[graph(graph_id="ev-heatmap"), graph(charts.event_factor_lines())]),
        footer("Problem day = pollen (any type) > 10 grains/m³, rain ≥ 1 mm or bad air (WHO limits). "
               "Pattern information, not medical advice."),
    ])


@app.callback(Output("ev-heatmap", "figure"), Input("ev-city", "value"))
def update_events(city):
    return charts.event_heatmap(city)


# ------------------------------- tab: Retail -------------------------------
def retail_tab():
    need = retail_need()
    peak_month = need.groupby("month")["high_days"].mean().idxmax()
    pm_month = need.groupby("month")["pm25_days"].mean().idxmax()
    pm25_city = need.groupby("city")["pm25_days"].sum().idxmax()
    return html.Div(className="tab-body business", children=[
        html.Div(className="filter-row", children=[dropdown("ret-city", CITIES, "Stockholm", "Highlight city")]),
        html.Div(className="kpi-row", children=[
            kpi_card(charts.MONTHS[peak_month - 1], "peak month for pollen products"),
            kpi_card(charts.MONTHS[pm_month - 1], "peak month for particle filters"),
            kpi_card(pm25_city, "most days with high fine particles (PM2.5)"),
        ]),
        html.Div(className="grid-2", children=[graph(graph_id="ret-pollen"), graph(graph_id="ret-pm")]),
        html.H3("Next step – A/B tests retailers can run with pollen data", className="section-title"),
        test_table(),
        footer("A/B test: design only – the project has no sales data. "
               "Pollen data: CAMS via Open-Meteo (model estimates). Pattern information, not medical advice."),
    ])


@app.callback(Output("ret-pollen", "figure"), Output("ret-pm", "figure"), Input("ret-city", "value"))
def update_retail(city):
    return charts.retail_heatmap("high_days", city), charts.retail_heatmap("pm25_days", city)


# Retail tab, last section: A/B test ideas
AB_TESTS = [
    ("Pollen alert email", "Regular newsletter",
     "\"Birch season is here\" email with allergy products", "Allergy-product sales per customer",
     "Customers (random split)", "Difference in means (t-test)"),
    ("Pollen-based website banner", "Regular banner",
     "Allergy banner on high-pollen days in the customer's city", "Conversion rate",
     "Website visitors (random split)", "Two-proportion z-test"),
    ("Campaign timing", "Campaign on the same fixed date every year",
     "Campaign starts when the data shows the season has started in the region", "Total season sales",
     "Regions / stores (geo-experiment)", "Difference-in-differences vs last year"),
    ("In-store placement", "Products in their usual aisle",
     "Products next to the checkout in high-pollen weeks", "Sales per store",
     "Stores (matched pairs by size and region)", "Difference-in-differences vs last year"),
]


def test_table():
    """A/B test ideas for retailers: one row per test, short labels instead of paragraphs."""
    header = html.Tr([html.Th(h) for h in ("Test", "Group A (control)", "Group B (treatment)", "Main metric",
                                           "Unit", "Analysis")])
    rows = [html.Tr([html.Td(test, className="test-name"), *[html.Td(v) for v in values]])
            for test, *values in AB_TESTS]
    return html.Div(className="test-table-wrap", children=html.Table(className="test-table",
                                                                     children=[html.Thead(header), html.Tbody(rows)]))


# ------------------------------- header: last update + "Update data" button -------------------------------
def update_box():
    """Last ingestion run, last day of data and whether it is up to date, plus the button that runs the
    pipeline (local only). The button is only active when there are new days to download."""
    ran_at, last_day = update.last_update()
    behind = update.days_behind(last_day)
    day = lambda d: f"{d.day} {d:%b}"   # '7 Oct' (no leading zero, works on Windows too)
    info = f"Latest data: {day(last_day)}"
    if behind == 0:
        # the next full day of data exists once tomorrow starts (the ingestion downloads up to yesterday)
        next_update = last_day + pd.Timedelta(days=2)
        state = html.Span(f" · ✅ Dashboard up to date · Next update: {day(next_update)} "
                          f"(new pollen data daily ~{pollen_release_time()})", className="update-ok")
    else:
        state = html.Span(f" · ⚠️ Update needed ({behind} day{'s' if behind > 1 else ''} missing)",
                          className="update-behind")
    last_run = f"Last download: {ran_at:%d %b %Y %H:%M}" if ran_at is not None else ""
    return html.Div(className="update-box", children=[
        html.Span([info, state], className="update-info", title=last_run),
        # hidden on Render (no database there), but kept in the layout so the callback always finds it
        # the status is in the text above; the button only turns grey (disabled) when there is nothing to download
        html.Button("🔄 Update data", id="update-btn", className="update-btn", n_clicks=0, disabled=behind == 0,
                    title=("The data already goes up to yesterday – nothing new to download" if behind == 0 else
                           "Download the new days, rebuild the tables (dbt) and reload the dashboard"),
                    style=None if update.can_update() else {"display": "none"}),
        dcc.Loading(html.Div(id="update-status", className="update-status"), type="dot"),
    ])


@app.callback(Output("update-status", "children"), Output("url", "href"),
              Input("update-btn", "n_clicks"), prevent_initial_call=True,
              running=[(Output("update-btn", "disabled"), True, False),
                       (Output("update-btn", "children"), "⏳ Updating…", "🔄 Update data")])
def press_update(n_clicks):
    """Run ingest → dbt build → snapshot. On success reload the page (new data on every tab); on failure
    say which step failed and keep the current data."""
    ok, results = update.run_update()
    if ok:
        return "", f"/?updated={n_clicks}"
    name, _, output = results[-1]
    return html.Span(f"❌ Update failed at: {name} – " + " ".join(output), className="update-error"), no_update


# ------------------------------- layout -------------------------------
def business_tab(label, children):
    """Tab of the Business group: orange when selected instead of blue (see style.css)."""
    return dcc.Tab(label=label, children=children, className="business-tab", selected_className="business-tab--selected")


def serve_layout():
    """Built on every page load (Dash calls the function), so after an update every tab shows the new data."""
    return html.Div(className="page", children=[
        dcc.Location(id="url", refresh=True),   # the update callback reloads the page through this
        html.Header(className="header", children=[html.H1("Pollen Radar Sweden"), update_box()]),
        # Group labels over the tabs (same 8 columns as the tabs): no label over the first 2 tabs ·
        # Customers over Weather & air · Business over Pharmacies → Retail · no label over Pollen now (last)
        html.Div(className="tab-groups", children=[
            html.Div(style={"gridColumn": "1 / 3"}),
            html.Div("Customers", className="tab-group customers"),
            html.Div("Business", className="tab-group business"),
        ]),
        dcc.Tabs(className="tabs", children=[
            dcc.Tab(label="Why this matters", children=why_this_matters()),
            dcc.Tab(label="Pollen calendar", children=pollen_calendar()),
            dcc.Tab(label="Weather & air", children=weather_and_air()),
            business_tab("Pharmacies", pharmacies()),
            business_tab("Tourism", tourism_tab()),
            business_tab("Events", events_tab()),
            business_tab("Retail", retail_tab()),
            dcc.Tab(label="Pollen now", children=pollen_now()),   # live view, last tab
        ]),
    ])


app.layout = serve_layout

if __name__ == "__main__":
    # Load all datasets once at start-up, so the first click on a filter is fast
    for load in (daily, season_days, rain_events, risk_days, hourly_profile, typical_seasons):
        load()
    app.run(debug=False)
