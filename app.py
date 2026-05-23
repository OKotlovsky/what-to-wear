"""
What to Wear — Ultra-minimal iPhone app
========================================
pip install streamlit requests
streamlit run app.py
"""

import streamlit as st
import requests
from datetime import date

# ── Page config ────────────────────────────────────────────────
st.set_page_config(
    page_title="What to Wear",
    page_icon="👗",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Geocode (cached 1 hr) ──────────────────────────────────────
@st.cache_data(ttl=3600)
def geocode(city: str) -> dict | None:
    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=6,
        )
        results = r.json().get("results")
        if not results:
            return None
        loc = results[0]
        return {"name": loc["name"], "country": loc.get("country",""),
                "lat": loc["latitude"], "lon": loc["longitude"]}
    except Exception:
        return None


# ── Weather fetch (cached 30 min) ──────────────────────────────
@st.cache_data(ttl=1800)
def get_weather(lat: float, lon: float, day: date) -> dict | None:
    """
    Returns temp_max (°C), temp_min (°C), precip_mm, wind_kph
    for a single day. Uses forecast endpoint if within 16 days,
    otherwise falls back to archive (last-year proxy).
    """
    from datetime import date as _date, timedelta
    today = _date.today()
    delta = (day - today).days
    base  = {"latitude": lat, "longitude": lon, "timezone": "auto",
             "daily": "temperature_2m_max,temperature_2m_min,"
                      "precipitation_sum,windspeed_10m_max"}

    # Pick endpoint
    if -365 <= delta <= 16:
        url   = ("https://api.open-meteo.com/v1/forecast" if delta >= 0
                 else "https://archive-api.open-meteo.com/v1/archive")
        s = e = day
    else:
        # proxy: same calendar window last year
        url   = "https://archive-api.open-meteo.com/v1/archive"
        s = e = day.replace(year=day.year - 1)

    try:
        r = requests.get(url, params={**base,
            "start_date": s.isoformat(), "end_date": e.isoformat()}, timeout=7)
        d = r.json().get("daily", {})
        if not d.get("time"):
            return None
        return {
            "temp_max":  d["temperature_2m_max"][0],
            "temp_min":  d["temperature_2m_min"][0],
            "precip_mm": d["precipitation_sum"][0] or 0,
            "wind_kph":  d["windspeed_10m_max"][0] or 0,
            "proxy":     delta > 16,
        }
    except Exception:
        return None


# ── Clothing ladder ────────────────────────────────────────────
def outfit(temp_max: float, precip_mm: float, wind_kph: float) -> tuple[str, str]:
    """
    Returns (emoji, directive_string).
    Single conditional ladder — no loops, no lists.
    """
    rain  = precip_mm > 2
    windy = wind_kph  > 35

    if temp_max >= 27:
        base = "Short shirt + Shorts"
        icon = "🩳"
    elif temp_max >= 20:
        base = "Short shirt + Long pants"
        icon = "👖"
    elif temp_max >= 13:
        base = "Long shirt + Light coat"
        icon = "🧥"
    elif temp_max >= 5:
        base = "Long shirt + Heavy coat"
        icon = "🧤"
    else:
        base = "Thermals + Heavy coat + Boots"
        icon = "❄️"

    if rain:
        base += " + Umbrella"
        icon  = "☂️"
    elif windy and temp_max < 20:
        base += " + Windproof layer"

    return icon, base


# ── Weather summary sentence ───────────────────────────────────
def weather_summary(w: dict) -> str:
    t   = f"{w['temp_max']:.0f}°C"
    p   = w["precip_mm"]
    spd = w["wind_kph"]

    parts = [t]
    if p > 5:   parts.append("rainy")
    elif p > 1: parts.append("light showers")
    if spd > 50: parts.append("very windy")
    elif spd > 35: parts.append("windy")

    suffix = " (estimated from last year)" if w.get("proxy") else ""
    return " and ".join(parts) + suffix


# ── Default city from IP ───────────────────────────────────────
@st.cache_data(ttl=3600)
def ip_city() -> str:
    try:
        return requests.get("http://ip-api.com/json/?fields=city",
                            timeout=3).json().get("city", "London")
    except Exception:
        return "London"


# ══════════════════════════════════════════════
#  UI
# ══════════════════════════════════════════════
st.markdown('<div class="app-title">👗 What to Wear?</div>', unsafe_allow_html=True)

city = st.text_input("Destination", value=ip_city(), label_visibility="visible",
                     placeholder="e.g. Paris, Tokyo, New York…")

travel_date = st.date_input("Date", value=date.today(), label_visibility="visible")

go = st.button("Check What to Wear")

# ── Result (only shown after button press) ─────────────────────
if go:
    if not city.strip():
        st.error("Please enter a destination.")
        st.stop()

    with st.spinner(""):
        loc = geocode(city.strip())
        if not loc:
            st.error(f"Can't find '{city}'. Try a nearby city.")
            st.stop()

        w = get_weather(loc["lat"], loc["lon"], travel_date)
        if not w:
            st.error("Weather data unavailable for that date. Try another date.")
            st.stop()

    icon, directive = outfit(w["temp_max"], w["precip_mm"], w["wind_kph"])
    summary         = weather_summary(w)
    date_str        = travel_date.strftime("%d %b %Y")

    st.markdown(f"""
    <div class="result-box">
      <div class="result-meta">📍 {loc['name']}, {loc['country']} · {date_str}</div>
      <div class="result-weather">{summary}</div>
      <div class="result-emoji">{icon}</div>
      <div class="result-outfit">{directive}</div>
    </div>
    """, unsafe_allow_html=True)
