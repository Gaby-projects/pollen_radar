"""Plotly charts for the dashboard, in the project style:
bold titles that state the conclusion, values >= 1000 as K/M, fixed colours, no dual y-axes."""
import datetime as dt

import pandas as pd
import plotly.graph_objects as go

from data import (ALL_CITIES, CITIES, HALF_MONTHS, HIGH_THRESHOLD, POLLEN, PREVALENCE, SEASON_CHANGE,
                  WEATHER_POLLEN, event_factors, pollen_for_date, event_risk, hourly_profile, intensity, rain_events, retail_need,
                  risk_calendar, risk_calendar_by_year, risk_days, season_coverage, season_days, spring_risk, start_gaps, stock_plan,
                  seasons, tourism, typical_seasons, weekly, weekly_by_year)

# Colours (same palette as the notebooks)
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
POLLEN_COLOURS = dict(zip(POLLEN, CATEGORICAL[:4]))       # alder blue, birch orange, grass aqua, mugwort yellow
BLUE = "#2a78d6"
BLUE_LIGHT = "#cde2fb"
GREY = "#e1e0d9"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
MUTED = "#898781"
FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"

# Sequential blue scale for heatmaps (light = low, dark = high)
BLUE_RAMP = ["#f3f7fd", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
BLUE_SCALE = [[i / (len(BLUE_RAMP) - 1), c] for i, c in enumerate(BLUE_RAMP)]

# Day of the year where each month starts (non-leap year) -> month labels on day-of-year axes
MONTH_STARTS = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def k_format(value):
    """1234 -> '1.2K', 2_500_000 -> '2.5M', 390 -> '390' (no thousands separators)."""
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}".rstrip("0").rstrip(".") + "M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f}".rstrip("0").rstrip(".") + "K"
    return f"{value:g}"


def base_layout(fig, title, subtitle=None, height=320):
    """Common look: bold title (+ optional subtitle), light grid, no chart border."""
    text = f"<b>{title}</b>" + (f"<br><span style='font-size:12px;color:{INK_SECONDARY}'>{subtitle}</span>" if subtitle else "")
    fig.update_layout(
        title={"text": text, "x": 0, "xanchor": "left", "font": {"size": 15, "color": INK}},
        font={"family": FONT, "color": INK_SECONDARY, "size": 12},
        height=height, margin={"l": 10, "r": 10, "t": 70 if subtitle else 50, "b": 30},
        plot_bgcolor="white", paper_bgcolor="white", showlegend=False,
        hoverlabel={"font": {"family": FONT}},
    )
    # automargin: make room for tick labels and axis titles so nothing is cut off
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=GREY, automargin=True)
    fig.update_yaxes(gridcolor=GREY, zeroline=False, automargin=True)
    return fig


# --------------------------- Tab 0: Why this matters ---------------------------
def prevalence_chart():
    fig = go.Figure(go.Bar(
        x=PREVALENCE["group"], y=PREVALENCE["percent"], marker_color=[BLUE_LIGHT, BLUE], width=0.5,
        text=[f"{p}%" for p in PREVALENCE["percent"]], textposition="outside", cliponaxis=False,
        hovertemplate="%{x}: %{y}% of adults<extra></extra>",
    ))
    fig.update_yaxes(range=[0, 55], ticksuffix="%", title=None)
    return base_layout(fig, "Pollen allergy is growing", "Adults in Stockholm County with pollen allergy")


# Darker steps of the pollen colours (same hues, darker steps of the palette ramps) – used where a bar
# should look heavier, e.g. the season-change chart on the first tab
POLLEN_COLOURS_DARK = {"Alder": "#256abf", "Birch": "#d95926", "Grass": "#199e70", "Mugwort": "#c98500"}


def season_change_chart():
    """One darker colour per pollen type; all labels in black, 'days earlier' in bold."""
    pollen = SEASON_CHANGE["change"].str.split().str[0]          # 'Birch season starts' -> 'Birch'
    colours = [POLLEN_COLOURS_DARK[p] for p in pollen]
    labels = [f"<b>{label}</b>" if days < 0 else label for label, days in zip(SEASON_CHANGE["label"], SEASON_CHANGE["days"])]
    fig = go.Figure(go.Bar(
        y=SEASON_CHANGE["change"], x=SEASON_CHANGE["days"].abs(), orientation="h", marker_color=colours,
        width=0.45, text=labels, textposition="outside", cliponaxis=False, textfont={"color": INK},
        hovertemplate="%{y} %{text}<extra></extra>",
    ))
    fig.update_xaxes(range=[0, 55], showticklabels=False, showgrid=False)
    fig = base_layout(fig, "Seasons start earlier and last longer", "Stockholm, today vs the early 1970s")
    # after base_layout, which sets grey axis text: the names next to the bars in black too
    fig.update_yaxes(autorange="reversed", gridcolor="white", ticksuffix="  ", tickfont={"color": INK})
    return fig


# --------------------------- Tab: Pollen calendar – season timeline ---------------------------
def pollen_timeline(city=ALL_CITIES):
    """One bar per pollen type over the whole year (darker pollen colours, text in black): light = season,
    dark = peak (±3 days so it stays visible).
    All cities: earliest start (south) → latest end (north) and earliest → latest peak; one city: its typical
    (median) season and peak day."""
    typical = typical_seasons() if city == ALL_CITIES else typical_seasons().query("city == @city")
    s = typical.groupby("pollen_type").agg(start=("start_doy", "min"), end=("end_doy", "max"),
                                           peak_from=("peak_doy", "min"), peak_to=("peak_doy", "max"))
    s = s.reindex(POLLEN)
    where = "all cities" if city == ALL_CITIES else city
    fig = go.Figure()
    fig.add_bar(y=s.index, x=s["end"] - s["start"], base=s["start"], orientation="h", width=0.55,
                marker={"color": [POLLEN_COLOURS_DARK[p] for p in s.index], "opacity": 0.35},
                text=[f"{doy_to_text(a)} – {doy_to_text(b)}" for a, b in zip(s["start"], s["end"])],
                textposition="outside", cliponaxis=False, textfont={"size": 11, "color": INK},
                hovertemplate="%{y}: %{text} (season, " + where + ")<extra></extra>")
    fig.add_bar(y=s.index, x=s["peak_to"] - s["peak_from"] + 6, base=s["peak_from"] - 3, orientation="h", width=0.55,
                marker_color=[POLLEN_COLOURS_DARK[p] for p in s.index],
                customdata=[f"{doy_to_text(a)} – {doy_to_text(b)}" if a != b else doy_to_text(a)
                            for a, b in zip(s["peak_from"], s["peak_to"])],
                hovertemplate="%{y}: peak %{customdata}<extra></extra>")
    fig.update_layout(barmode="overlay")
    month_axis(fig)
    first, last = doy_to_text(s["start"].min()), doy_to_text(s["end"].max())
    if city == ALL_CITIES:
        title, subtitle = "Pollen season runs from late February to mid-August", \
            "Typical season in Sweden, south → north · dark = peak weeks · 2021–2026"
    else:
        title, subtitle = f"Pollen season in {city}: {first} – {last}", \
            f"Typical season in {city} · dark = peak · median 2021–2026"
    fig = base_layout(fig, title, subtitle, height=280)
    # after base_layout, which sets grey axis text: the pollen names next to the bars in black
    fig.update_yaxes(autorange="reversed", gridcolor="white", ticksuffix="  ", tickfont={"color": INK})
    return fig


# --------------------------- Date helpers (shared by several tabs) ---------------------------
def doy_to_text(doy):
    """Day of year -> '15 Apr' (non-leap calendar)."""
    return (dt.date(2023, 1, 1) + dt.timedelta(days=int(round(doy)) - 1)).strftime("%d %b").lstrip("0")


def month_axis(fig, first_month=1, last_month=12):
    """Day-of-year x-axis labelled with month names."""
    fig.update_xaxes(tickvals=MONTH_STARTS[first_month - 1:last_month], ticktext=MONTHS[first_month - 1:last_month],
                     range=[MONTH_STARTS[first_month - 1] - 3, (MONTH_STARTS + [366])[last_month] + 3],
                     showgrid=True, gridcolor=GREY)
    return fig


# --------------------------- Tab: Pollen now – charts for the selected date ---------------------------
# Pollen now charts: ~10 grains/m³ is where sensitive people start to notice symptoms (any pollen type) – the same
# level used for a 'pollen day' in the Events tab. The y-axis goes to at least 15, so this line is always
# visible and traces (e.g. 0.1) look flat instead of filling the chart.
SYMPTOM_LEVEL = 10
LIVE_Y_MIN = 15


def _live_y_axis(fig, values):
    top = values.max().max()
    fig.update_yaxes(title={"text": "grains/m³", "font": {"size": 11}},
                     range=[0, max(LIVE_Y_MIN, (top if pd.notna(top) else 0) * 1.1)])
    fig.add_hline(y=SYMPTOM_LEVEL, line={"color": CATEGORICAL[4], "width": 1.5, "dash": "dot"},
                  annotation_text=f"{SYMPTOM_LEVEL} = symptoms start", annotation_position="top left",
                  annotation_font={"size": 10, "color": INK_SECONDARY})


def _updated(now, fetched_at):
    """Subtitle text: hour of the model data + when the API was called."""
    return f"data for {now:%H:00} · updated {fetched_at:%H:%M} from the Open-Meteo API"


def _no_data(fig, title, text):
    fig.add_annotation(text=text, showarrow=False, font={"color": MUTED})
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return base_layout(fig, title, "Open-Meteo API", height=300)


def _source_note(src, day):
    """Subtitle part that says where the data for a non-live date comes from."""
    if src["kind"] == "history":
        return "historical data (CAMS model via Open-Meteo, stored in DuckDB)"
    if src["kind"] == "recent":
        return f"Open-Meteo API, not in the database yet · retrieved {src['fetched_at']:%H:%M}"
    if src["kind"] == "forecast":
        return f"Open-Meteo API forecast · retrieved {src['fetched_at']:%H:%M}"
    years = src["years"]
    return f"average of the same dates in {len(years)} years ({years[0]}–{years[-1]}) – not a forecast"


def _pollen_lines(fig, hourly, mode="lines", hover="%a %d %b %H:00"):
    for p in POLLEN:
        fig.add_scatter(x=hourly["time"], y=hourly[f"{p.lower()}_pollen"], mode=mode, name=p,
                        line={"color": POLLEN_COLOURS[p], "width": 2}, marker={"size": 4},
                        hovertemplate=p + ", %{x|" + hover + "}: %{y:.1f} grains/m³<extra></extra>")


def _day_summary(hourly):
    """For the titles: (summary, peak text or None). Summary: 'no pollen' | 'only traces of grass pollen
    (max 0.1 grains/m³)' | 'birch up to 140 grains/m³ (high)'; peak text: 'birch peaks at 16:00 (140 grains/m³, high)'."""
    peaks = {p: hourly[f"{p.lower()}_pollen"].max() for p in POLLEN}
    top = max(peaks, key=lambda p: peaks[p] if pd.notna(peaks[p]) else -1)
    if not peaks[top] > 0:
        return "no pollen", None
    if peaks[top] < 1:
        return f"only traces of {top.lower()} pollen (max {peaks[top]:.1f} grains/m³)", None
    peak_hour = hourly.loc[hourly[f"{top.lower()}_pollen"].idxmax(), "time"]
    high = peaks[top] > HIGH_THRESHOLD[top]
    return (f"{top.lower()} up to {peaks[top]:.0f} grains/m³" + (" (high)" if high else ""),
            f"{top.lower()} peaks at {peak_hour:%H:00} ({peaks[top]:.0f} grains/m³" + (", high)" if high else ")"))


def _mark_selected_day(fig, day):
    """Light band over the selected date in the week chart."""
    start = pd.Timestamp(day)
    fig.add_vrect(x0=start, x1=start + pd.Timedelta(days=1), fillcolor=BLUE_LIGHT, opacity=0.45, line_width=0,
                  layer="below", annotation_text="selected day", annotation_position="top left",
                  annotation_font={"size": 10, "color": INK_SECONDARY})


def _mark_now(fig, now, until):
    """Live only: forecast hours shaded grey + a dashed 'now' line."""
    fig.add_vrect(x0=now, x1=until, fillcolor=GREY, opacity=0.35, line_width=0, layer="below")
    fig.add_vline(x=now, line={"color": INK_SECONDARY, "width": 1, "dash": "dash"})
    fig.add_annotation(x=now, y=1, yref="paper", text="now", showarrow=False, xanchor="left", yanchor="bottom",
                       font={"size": 11, "color": INK_SECONDARY})


def _next_season_text(city, day):
    seasons = typical_seasons().query("city == @city").set_index("pollen_type")
    doy = pd.Timestamp(day).dayofyear
    upcoming = [(s if s > doy else s + 365, p) for p, s in seasons["start_doy"].items()]
    next_start, pollen = min(upcoming)
    return f"next up is {pollen.lower()}, around {doy_to_text(next_start % 365 or 365)}"


def _finish(fig, title, subtitle, values):
    _live_y_axis(fig, values[[f"{p.lower()}_pollen" for p in POLLEN]])
    fig = base_layout(fig, title, subtitle, height=300)
    fig.update_layout(showlegend=True, legend={"orientation": "h", "y": -0.2, "x": 0})
    return fig


# Title start per data source (non-live dates); the live titles are built in the functions
WEEK_PREFIX = {"history": "{city} around {day:%d %b %Y}", "recent": "{city} around {day:%d %b %Y}",
               "forecast": "Forecast for {city} around {day:%d %b}", "typical": "Typical pollen in {city} around {day:%d %b}"}
DAY_PREFIX = {"history": "{city} on {day:%d %b %Y}", "recent": "{city} on {day:%d %b %Y}",
              "forecast": "Forecast for {city} on {day:%d %b}", "typical": "Typical day in {city} for {day:%d %b}"}


def week_chart(city, day=None):
    """Pollen around the selected date, one line per pollen type: 2 days before → 4 days after.
    Today = live from the Open-Meteo API (forecast shaded, 'now' line, titles say 'Live').
    Other dates = historical data, the API forecast or the typical values (see data.pollen_for_date),
    with the selected day marked."""
    day = day or pd.Timestamp.now(tz="Europe/Stockholm").date()
    fig = go.Figure()
    src = pollen_for_date(city, day)
    if src is None:
        return _no_data(fig, f"Live this week in {city}", "Live data unavailable – the Open-Meteo API could not be reached")
    hourly = src["hourly"]
    if hourly.empty:
        return _no_data(fig, f"{city} around {day:%d %b %Y}", "No data for these dates")
    if src["kind"] == "live":
        now = pd.Timestamp(src["current"]["time"])
        _mark_now(fig, now, hourly["time"].max())
        values = {p: src["current"][f"{p.lower()}_pollen"] or 0 for p in POLLEN}
        top = max(values, key=values.get)
        if values[top] < 1:
            title = f"Live this week: no pollen in the air in {city} right now"
        else:
            level = "high" if values[top] > HIGH_THRESHOLD[top] else "in the air"
            title = f"Live this week: {top.lower()} pollen is {level} in {city} – {values[top]:.0f} grains/m³"
        subtitle = f"Last 2 days + 4-day forecast (grey) · {_updated(now, src['fetched_at'])}"
    else:
        _mark_selected_day(fig, day)
        summary, _ = _day_summary(hourly[hourly["time"].dt.date == day])
        title = f"{WEEK_PREFIX[src['kind']].format(city=city, day=day)}: {summary} on the selected day"
        subtitle = f"{hourly['time'].min():%d %b} – {hourly['time'].max():%d %b} · {_source_note(src, day)}"
    _pollen_lines(fig, hourly)
    fig.update_xaxes(tickformat="%a %d %b", showgrid=True, gridcolor=GREY)
    return _finish(fig, title, subtitle, hourly)


def day_chart(city, day=None):
    """The selected date hour by hour (00:00–23:00, Swedish time), same data source as week_chart.
    Today = live: hours after now are the forecast (shaded); with no pollen the title names the next season."""
    day = day or pd.Timestamp.now(tz="Europe/Stockholm").date()
    fig = go.Figure()
    src = pollen_for_date(city, day)
    if src is None:
        return _no_data(fig, f"Live today in {city}", "Live data unavailable – the Open-Meteo API could not be reached")
    hours = src["hourly"][src["hourly"]["time"].dt.date == day]
    if hours.empty:
        return _no_data(fig, f"{city} on {day:%d %b %Y}", "No data for this date")
    start = pd.Timestamp(day)
    end = start + pd.Timedelta(hours=23)
    summary, peak = _day_summary(hours)
    peak = peak or summary
    if src["kind"] == "live":
        now = pd.Timestamp(src["current"]["time"])
        _mark_now(fig, now, end)
        if summary == "no pollen":
            peak = f"no pollen – {_next_season_text(city, day)}"
        title = f"Live today in {city}: {peak}"
        subtitle = f"{now:%A %d %b}, hour by hour · grey = forecast · {_updated(now, src['fetched_at'])}"
    else:
        title = f"{DAY_PREFIX[src['kind']].format(city=city, day=day)}: {peak}"
        subtitle = f"{day:%A %d %b %Y}, hour by hour · {_source_note(src, day)}"
    _pollen_lines(fig, hours, mode="lines+markers", hover="%H:00")
    fig.update_xaxes(range=[start - pd.Timedelta(minutes=30), end + pd.Timedelta(minutes=30)],
                     tickformat="%H:00", dtick=3 * 3600 * 1000, showgrid=True, gridcolor=GREY)
    return _finish(fig, title, subtitle, hours)


# --------------------------- Tab: Pollen calendar ---------------------------
def _cities(city):
    """All six cities (south → north), or only the selected one."""
    return CITIES if city == ALL_CITIES else [city]


def calendar_heatmap(pollen, city=ALL_CITIES):
    """All cities: one row per city (average 2021–2026). One city: one row per year, so the cells keep a normal
    shape and the years can be compared."""
    if city == ALL_CITIES:
        grid = (weekly().query("pollen_type == @pollen")
                .pivot(index="city", columns="iso_week", values="grains").reindex(CITIES))
        title, subtitle = f"{pollen} pollen through the year", "Average per week 2021–2026 · south (top) → north"
    else:
        data = weekly_by_year().query("pollen_type == @pollen and city == @city")
        grid = data.pivot(index="iso_year", columns="iso_week", values="grains")
        grid.index = grid.index.astype(str)
        title, subtitle = f"{pollen} pollen through the year in {city}", "Average per week, one row per year"
    fig = go.Figure(go.Heatmap(
        z=grid.values, x=grid.columns, y=grid.index, colorscale=BLUE_SCALE, xgap=1, ygap=1,
        colorbar={"title": {"text": "grains/m³", "side": "right"}, "thickness": 12},
        hovertemplate="%{y}, week %{x}: %{z:.1f} grains/m³<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed", gridcolor="white", type="category")
    fig.update_xaxes(title=None, tickvals=list(range(5, 53, 5)), ticktext=[f"w{w}" for w in range(5, 53, 5)])
    return base_layout(fig, title, subtitle)


def season_bars(pollen, city=ALL_CITIES):
    """All cities: typical season per city. One city: that city's real season per year, to compare years."""
    if city == ALL_CITIES:
        data = typical_seasons().query("pollen_type == @pollen").set_index("city").reindex(CITIES).reset_index()
        labels = data["city"]
        title, subtitle = f"{pollen} season per city", "Typical start → end (bar) and peak (dot), median 2021–2026"
    else:
        data = seasons().query("pollen_type == @pollen and city == @city").sort_values("year")
        labels = data["year"].astype(str)
        title, subtitle = f"{pollen} season in {city} per year", "Start → end (bar) and peak (dot) of each season"
    fig = go.Figure()
    fig.add_bar(y=labels, x=data["end_doy"] - data["start_doy"], base=data["start_doy"], orientation="h",
                marker_color=POLLEN_COLOURS[pollen], width=0.5,
                customdata=list(zip(data["start_doy"].map(doy_to_text), data["peak_doy"].map(doy_to_text),
                                    data["end_doy"].map(doy_to_text))),
                hovertemplate="%{y}: %{customdata[0]} → peak %{customdata[1]} → %{customdata[2]}<extra></extra>")
    fig.add_scatter(y=labels, x=data["peak_doy"], mode="markers", hoverinfo="skip",
                    marker={"color": INK, "size": 9, "line": {"color": "white", "width": 1.5}})
    fig.update_yaxes(autorange="reversed", gridcolor="white", type="category")
    month_axis(fig, 2, 9)
    return base_layout(fig, title, subtitle)


def hour_profile(city, pollen):
    """Pollen by hour of the day as an index (100 = daily average); 'All cities' = average of the six."""
    data = hourly_profile().query("pollen_type == @pollen and city in @cities", local_dict={
        "pollen": pollen, "cities": _cities(city)})
    data = data.groupby("hour_local", as_index=False)["index"].mean()
    low = data.loc[data["index"].idxmin()]
    fig = go.Figure()
    fig.add_hline(y=100, line={"color": MUTED, "dash": "dash", "width": 1})
    fig.add_scatter(x=data["hour_local"], y=data["index"], mode="lines",
                    line={"color": POLLEN_COLOURS[pollen], "width": 2},
                    hovertemplate="%{x}:00 – index %{y:.0f}<extra></extra>")
    fig.add_scatter(x=[low["hour_local"]], y=[low["index"]], mode="markers+text",
                    text=[f"{int(low['hour_local']):02d}:00"], textposition="bottom center",
                    marker={"color": INK, "size": 9}, hoverinfo="skip")
    fig.update_xaxes(title=None, tickvals=list(range(0, 24, 3)), ticktext=[f"{h:02d}:00" for h in range(0, 24, 3)])
    fig.update_yaxes(title=None)
    where = "average of all cities" if city == ALL_CITIES else city
    return base_layout(fig, f"Lowest pollen at {int(low['hour_local']):02d}:00",
                       f"{pollen}, {where} · index by hour (100 = daily average)")


def risk_calendar_chart(city=ALL_CITIES):
    """All cities: one row per city. One city: one row per year (normal cell shape, years can be compared)."""
    if city == ALL_CITIES:
        grid = risk_calendar().pivot(index="city", columns="week", values="high_any").reindex(CITIES)
        title, subtitle = "Allergy risk calendar", \
            "Share of high-pollen days per week (any pollen type), all cities · lighter = safer"
    else:
        grid = (risk_calendar_by_year().query("city == @city")
                .pivot(index="year", columns="week", values="high_any"))
        grid.index = grid.index.astype(str)
        title, subtitle = f"Allergy risk calendar in {city}", \
            "Share of high-pollen days per week (any pollen type), one row per year · lighter = safer"
    fig = go.Figure(go.Heatmap(
        z=grid.values, x=grid.columns, y=grid.index, colorscale=BLUE_SCALE, zmin=0, zmax=1, xgap=1, ygap=1,
        colorbar={"title": {"text": "days", "side": "right"}, "tickformat": ".0%", "thickness": 12},
        hovertemplate="%{y}, week %{x}: %{z:.0%} high-pollen days<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed", gridcolor="white", type="category")
    fig.update_xaxes(title=None, tickvals=list(range(10, 39, 4)), ticktext=[f"w{w}" for w in range(10, 39, 4)])
    return base_layout(fig, title, subtitle)


# --------------------------- Tab: Weather & air ---------------------------
def _city_filter(df, city):
    return df if city == ALL_CITIES else df[df["city"] == city]


def weather_effect(city, variable):
    """Pollen vs the average season day (×) by rain / wind / temperature group, per pollen type."""
    data = _city_filter(season_days(), city)
    order = list(data[variable].cat.categories)
    stats = data.groupby(["pollen_type", variable], observed=True)["ratio"].agg(["mean", "size"]).reset_index()
    stats = stats[stats["size"] >= 15]            # hide groups with too few days
    fig = go.Figure()
    fig.add_hline(y=1, line={"color": MUTED, "dash": "dash", "width": 1})
    for p in WEATHER_POLLEN:
        s = stats[stats["pollen_type"] == p].set_index(variable).reindex(order).reset_index()
        fig.add_scatter(x=s[variable], y=s["mean"], name=p, mode="lines+markers",
                        line={"color": POLLEN_COLOURS[p], "width": 2}, marker={"size": 7},
                        hovertemplate=p + ", %{x}: %{y:.2f}× average day<extra></extra>")
    fig.update_yaxes(rangemode="tozero", title=None, ticksuffix="×")   # auto range: some cities go above 2×
    fig.update_xaxes(title=None, categoryorder="array", categoryarray=order)
    title = {"Rain": "Rain cuts pollen", "Wind": "Wind: smaller effect", "Temperature": "Warm days raise pollen"}[variable]
    fig = base_layout(fig, title, f"{variable} · pollen vs average season day", height=300)
    fig.update_layout(showlegend=True, legend={"orientation": "h", "y": -0.15, "x": 0})
    return fig


def recovery_curve(city):
    ev = _city_filter(rain_events(), city)
    fig = go.Figure()
    for p in WEATHER_POLLEN:
        g = ev[ev["pollen_type"] == p]
        if len(g) == 0:
            continue
        share = [(g["recovery_days"] <= k).mean() for k in range(0, 8)]
        fig.add_scatter(x=list(range(0, 8)), y=share, name=f"{p} (n={len(g)})", mode="lines+markers",
                        line={"color": POLLEN_COLOURS[p], "width": 2}, marker={"size": 6},
                        hovertemplate=p + ", day %{x}: %{y:.0%} recovered<extra></extra>")
    fig.update_yaxes(range=[0, 1], tickformat=".0%", title=None)
    fig.update_xaxes(title={"text": "days after the rain day", "font": {"size": 11}}, dtick=1)
    fig = base_layout(fig, "Pollen comes back within ~2 days", "Rain events back to ≥ 80% of the pre-rain level")
    fig.update_layout(showlegend=True, legend={"orientation": "h", "y": -0.25, "x": 0})
    return fig


def risk_by_year(city):
    r = _city_filter(risk_days(), city)
    per_year = r.groupby("year")["both"].sum()
    if city == ALL_CITIES:
        per_year = per_year / len(CITIES)
    fig = go.Figure(go.Bar(x=per_year.index.astype(str), y=per_year.values, marker_color=BLUE, width=0.6,
                           text=[f"{v:.0f}" if city != ALL_CITIES else f"{v:.1f}" for v in per_year.values],
                           textposition="outside", cliponaxis=False,
                           hovertemplate="%{x}: %{y:.1f} days<extra></extra>"))
    fig.update_yaxes(title=None, rangemode="tozero")
    sub = "average per city" if city == ALL_CITIES else city
    return base_layout(fig, "High pollen + bad air days", f"Days per year, {sub} (bad air = WHO limits)")


def risk_by_month(city):
    r = _city_filter(risk_days(), city)
    r = r[r["both"]]
    counts = r.groupby(["month", "cause"]).size().unstack(fill_value=0).reindex(range(3, 10), fill_value=0)
    fig = go.Figure()
    for cause, colour in [("Ozone", CATEGORICAL[0]), ("PM2.5 (fine particles)", CATEGORICAL[1])]:
        if cause in counts:
            fig.add_bar(x=[MONTHS[m - 1] for m in counts.index], y=counts[cause], name=cause, marker_color=colour,
                        marker_line={"color": "white", "width": 2},
                        hovertemplate=cause + ", %{x}: %{y} days<extra></extra>")
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title=None)
    fig = base_layout(fig, "Mostly ozone, mostly in May", "Risk days by month and cause, 2021–2026")
    fig.update_layout(showlegend=True, legend={"orientation": "h", "y": -0.15, "x": 0})
    return fig


# --------------------------- Tab: Pharmacies ---------------------------
def _bold_city(city):
    return {"tickvals": CITIES, "ticktext": [f"<b>{c}</b>" if c == city else c for c in CITIES]}


def _dim_other_rows(fig, city):
    """Heatmap with one row per city: cover the rows of the other cities with a light veil,
    so the selected city stands out. 'All cities' keeps every row in full colour."""
    if city == ALL_CITIES:
        return
    for i, c in enumerate(CITIES):
        if c != city:
            fig.add_shape(type="rect", xref="paper", x0=0, x1=1, yref="y", y0=i - 0.5, y1=i + 0.5,
                          fillcolor="white", opacity=0.75, line={"width": 0}, layer="above")


def _city_colours(city, colour, other):
    """Full colour for the selected city (or every city when 'All cities' is selected), other colour for the rest."""
    return [colour if city in (c, ALL_CITIES) else other for c in CITIES]


def planning_heatmap(pollen, city):
    cov = season_coverage().query("pollen_type == @pollen")
    grid = cov.pivot(index="city", columns="week", values="in_season").reindex(CITIES)
    plan = stock_plan().query("pollen_type == @pollen").set_index("city").reindex(CITIES)
    fig = go.Figure(go.Heatmap(
        z=grid.values, x=grid.columns, y=grid.index, colorscale=BLUE_SCALE, zmin=0, zmax=1, xgap=1, ygap=1,
        colorbar={"title": {"text": "years", "side": "right"}, "tickformat": ".0%", "thickness": 12},
        hovertemplate="%{y}, week %{x}: in season %{z:.0%} of years<extra></extra>",
    ))
    fig.add_scatter(x=plan["stock_ready_week"], y=plan.index, mode="markers+text",
                    marker={"symbol": "triangle-down", "size": 13, "color": _city_colours(city, CATEGORICAL[1], GREY)},
                    text=[f"w{w}" for w in plan["stock_ready_week"]], textposition="middle left",
                    textfont={"size": 10, "color": _city_colours(city, INK, MUTED)}, showlegend=False,
                    hovertemplate="%{y}: stock ready by week %{x}<extra></extra>")
    _dim_other_rows(fig, city)
    fig.update_yaxes(autorange="reversed", gridcolor="white", **_bold_city(city))
    fig.update_xaxes(title=None, tickvals=list(range(6, 37, 3)), ticktext=[f"w{w}" for w in range(6, 37, 3)])
    return base_layout(fig, f"When to stock up: {pollen.lower()} season per city",
                       "Share of years the week was in season · ▼ = have stock ready by this week", height=340)


def gap_chart(pollen, city):
    g = start_gaps().query("pollen_type == @pollen").set_index("city").reindex(CITIES).reset_index()
    colours = _city_colours(city, POLLEN_COLOURS[pollen], MUTED)
    fig = go.Figure()
    fig.add_vline(x=0, line={"color": MUTED, "dash": "dash", "width": 1})
    for _, r in g.iterrows():
        fig.add_shape(type="line", x0=r["earliest"], x1=r["latest"], y0=r["city"], y1=r["city"],
                      line={"color": GREY, "width": 4})
    fig.add_scatter(x=g["median"], y=g["city"], mode="markers", marker={"size": 12, "color": colours,
                    "line": {"color": "white", "width": 1.5}},
                    customdata=g[["earliest", "latest"]].round(1),
                    hovertemplate="%{y}: %{x:.1f} weeks after Malmö (range %{customdata[0]}–%{customdata[1]})<extra></extra>")
    fig.update_yaxes(autorange="reversed", gridcolor="white", **_bold_city(city))
    fig.update_xaxes(title={"text": "weeks after Malmö", "font": {"size": 11}}, zeroline=False)
    return base_layout(fig, "The season moves south → north", "Median weeks after Malmö (dot) and range between years (bar)")


def intensity_heatmap(pollen, city):
    data = intensity().query("pollen_type == @pollen")
    grid = data.pivot(index="city", columns="year", values="index").reindex(CITIES)
    diverging = [[0, "#256abf"], [0.5, "#f0efec"], [1, "#e34948"]]
    fig = go.Figure(go.Heatmap(
        z=grid.values, x=[str(y) for y in grid.columns], y=grid.index, colorscale=diverging, zmin=50, zmax=150,
        xgap=2, ygap=2, texttemplate="%{z:.0f}", textfont={"size": 11},
        colorbar={"title": {"text": "index", "side": "right"}, "thickness": 12},
        hovertemplate="%{y} %{x}: %{z:.0f} (100 = city average)<extra></extra>",
    ))
    _dim_other_rows(fig, city)
    fig.update_yaxes(autorange="reversed", gridcolor="white", **_bold_city(city))
    return base_layout(fig, "Which years were intense?", "Season intensity, 100 = city average · red = above, blue = below")


def yearly_pollen_bars(pollen, city):
    plan = stock_plan().query("pollen_type == @pollen").set_index("city").reindex(CITIES).reset_index()
    colours = _city_colours(city, POLLEN_COLOURS[pollen], BLUE_LIGHT)
    fig = go.Figure(go.Bar(x=plan["city"], y=plan["yearly_pollen"], marker_color=colours, width=0.6,
                           text=[k_format(round(v)) for v in plan["yearly_pollen"]], textposition="outside",
                           cliponaxis=False, hovertemplate="%{x}: %{y:,.0f} grains/m³ per season<extra></extra>"))
    fig.update_yaxes(title=None, showticklabels=False, showgrid=False)
    return base_layout(fig, "Where demand is biggest", f"Average {pollen.lower()} pollen per season (sum of daily values)")


# --------------------------- Tabs: Tourism, Events and Retail ---------------------------
def tourism_heatmap(city):
    data = tourism()
    grid = data.pivot(index="city", columns="period", values="high_any").reindex(index=CITIES, columns=HALF_MONTHS)
    fig = go.Figure(go.Heatmap(
        z=grid.values, x=grid.columns, y=grid.index, colorscale=BLUE_SCALE, zmin=0, zmax=0.75, xgap=2, ygap=2,
        texttemplate="%{z:.0%}", textfont={"size": 11}, showscale=False,
        hovertemplate="%{y}, %{x}: %{z:.0%} high-pollen days<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed", gridcolor="white", **_bold_city(city))
    return base_layout(fig, "Tourism: spring destinations", "High-pollen days per half-month · lighter = better destination", height=340)


def event_heatmap(city):
    grid = event_risk().pivot(index="city", columns="week", values="problem").reindex(CITIES)
    fig = go.Figure(go.Heatmap(
        z=grid.values, x=grid.columns, y=grid.index, colorscale=BLUE_SCALE, zmin=0, zmax=1, xgap=1, ygap=1,
        colorbar={"title": {"text": "days", "side": "right"}, "tickformat": ".0%", "thickness": 12},
        hovertemplate="%{y}, week %{x}: %{z:.0%} problem days<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed", gridcolor="white", **_bold_city(city))
    fig.update_xaxes(title=None, tickvals=list(range(14, 39, 3)), ticktext=[f"w{w}" for w in range(14, 39, 3)])
    return base_layout(fig, "Events: best weeks are late August", "Days with pollen > 10, rain ≥ 1 mm or bad air · lighter = better", height=340)


def spring_bars(city):
    data = spring_risk().set_index("city").reindex(CITIES).reset_index()
    colours = [BLUE if c == city else BLUE_LIGHT for c in data["city"]]
    fig = go.Figure(go.Bar(x=data["city"], y=data["high_any"], marker_color=colours, width=0.6,
                           text=[f"{v:.0%}" for v in data["high_any"]], textposition="outside", cliponaxis=False,
                           hovertemplate="%{x}: %{y:.0%} high-pollen days in April–June<extra></extra>"))
    fig.update_yaxes(title=None, showticklabels=False, showgrid=False, range=[0, data["high_any"].max() * 1.25])
    return base_layout(fig, "Whole spring: fewest high-pollen days in the north",
                       "Share of high-pollen days April–June, 2021–2026 · lower = better", height=340)


def event_factor_lines():
    data = event_factors()
    colours = {"Rain (≥ 1 mm)": CATEGORICAL[0], "Bad air (PM2.5 or ozone)": CATEGORICAL[4],
               "Hot (≥ 25 °C)": CATEGORICAL[3]}
    fig = go.Figure()
    for factor, colour in colours.items():
        f = data[data["factor"] == factor]
        fig.add_scatter(x=f["week"], y=f["share"], name=factor, mode="lines+markers",
                        line={"color": colour, "width": 2}, marker={"size": 5},
                        hovertemplate=factor + ", week %{x}: %{y:.0%} of days<extra></extra>")
    fig.update_yaxes(tickformat=".0%", title=None, rangemode="tozero")
    fig.update_xaxes(title=None, tickvals=list(range(14, 39, 3)), ticktext=[f"w{w}" for w in range(14, 39, 3)])
    fig = base_layout(fig, "Rain is the most frequent spoiler", "Share of days per week, average of the 6 cities", height=340)
    fig.update_layout(showlegend=True, legend={"orientation": "h", "y": -0.18, "x": 0})
    return fig


def retail_heatmap(field, city):
    need = retail_need()
    grid = need.pivot(index="city", columns="month", values=field).reindex(CITIES)
    labels = [[f"{v:.0f}" if v >= 0.5 else "" for v in row] for row in grid.values]
    fig = go.Figure(go.Heatmap(
        z=grid.values, x=[MONTHS[m - 1] for m in grid.columns], y=grid.index, colorscale=BLUE_SCALE, xgap=2, ygap=2,
        text=labels, texttemplate="%{text}", textfont={"size": 11}, showscale=False,
        hovertemplate="%{y}, %{x}: %{z:.1f} days<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed", gridcolor="white", **_bold_city(city))
    if field == "high_days":
        return base_layout(fig, "Retail: pollen products peak in April–May", "High-pollen days per month")
    return base_layout(fig, "Retail: particle filters in Feb–March", "Days with PM2.5 (fine particles) above the WHO limit per month")
