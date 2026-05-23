"""
What to Wear — Ultra-minimal iPhone app
========================================
pip install streamlit requests
streamlit run app.py
"""

import streamlit as st
import requests
from datetime import date, timedelta

# ── Page config ────────────────────────────────────────────────
st.set_page_config(
    page_title="What to Wear",
    page_icon="👗",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── CSS ────────────────────────────────────────────────────────
st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<meta name="apple-mobile-web-app-capable" content="yes">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
*, html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, sans-serif !important;
}
#MainMenu, footer, header { display: none !important; }
.stApp { background: #f0f2f5; }
.block-container {
    padding: 2rem 1.2rem !important;
    max-width: 380px !important;
    margin: auto !important;
}
.app-title {
    text-align: center;
    font-size: 1.3rem;
    font-weight: 800;
    color: #1a1a2e;
    margin-bottom: 1.4rem;
}
.stButton > button {
    width: 100% !important;
    border-radius: 14px !important;
    background: linear-gradient(135deg, #667eea, #764ba2) !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 0.75rem !important;
    border: none !important;
    margin-top: 0.4rem !important;
    box-shadow: 0 4px 18px rgba(102,126,234,0.38) !important;
}
.result-box {
    margin-top: 1.2rem;
    background: white;
    border-radius: 20px;
    padding: 1.3rem 1.2rem;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
}
.result-meta    { font-size: 0.75rem; font-weight: 600; color: #8b9ab1;
                  text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.4rem; }
.result-weather { font-size: 0.95rem; color: #4a5568; margin-bottom: 0.6rem; }
.result-emoji   { font-size: 2.2rem; margin-bottom: 0.3rem; }
.result-outfit  { font-size: 1.3rem; font-weight: 800; color: #1a1a2e; }
</style>
""", unsafe_allow_html=True)


# ── Geocode ────────────────────────────────────────────────────
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
        return {"name": loc["name"], "country": loc.get("country", ""),
                "lat": loc["latitude"], "lon": loc["longitude"]}
    except Exception:
        return None


# ── Weather fetch (FIXED) ──────────────────────────────────────
@st.cache_data(ttl=1800)  # cache keyed on lat/lon/day — prevents repeat API hits
def get_weather(lat: float, lon: float, day: date) -> dict | None:
    """
    Routing logic:
      • today / next 15 days  → forecast endpoint
      • past > 2 days         → archive endpoint
      • future > 15 days      → archive using same date last year (climate proxy)
    Retries up to 3 times with backoff on 429 rate-limit errors.
    """
    import time

    today = date.today()
    delta = (day - today).days

    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    ARCHIVE_URL  = "https://archive-api.open-meteo.com/v1/archive"
    daily_vars   = ("temperature_2m_max,temperature_2m_min,"
                    "precipitation_sum,windspeed_10m_max")

    if 0 <= delta <= 15:
        url, req_date, is_proxy = FORECAST_URL, day, False
    elif -2 <= delta < 0:
        url, req_date, is_proxy = FORECAST_URL, day, False
    elif delta < -2:
        url, req_date, is_proxy = ARCHIVE_URL, day, False
    else:
        try:
            req_date = day.replace(year=day.year - 1)
        except ValueError:
            req_date = day.replace(year=day.year - 1, day=28)
        url, is_proxy = ARCHIVE_URL, True

    params = {
        "latitude":   lat,
        "longitude":  lon,
        "timezone":   "auto",
        "daily":      daily_vars,
        "start_date": req_date.isoformat(),
        "end_date":   req_date.isoformat(),
    }

    # ── Retry loop: 3 attempts with 1s / 3s backoff on 429 ──
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, timeout=8)
            if r.status_code == 429:
                time.sleep(2 ** attempt)   # 1s, 2s, 4s
                continue
            r.raise_for_status()
            d = r.json().get("daily", {})
            if not d.get("time"):
                return None
            return {
                "temp_max":  d["temperature_2m_max"][0],
                "temp_min":  d["temperature_2m_min"][0],
                "precip_mm": d["precipitation_sum"][0] or 0,
                "wind_kph":  d["windspeed_10m_max"][0] or 0,
                "proxy":     is_proxy,
            }
        except requests.exceptions.RequestException:
            time.sleep(2 ** attempt)

    return None  # all retries exhausted


# ── Clothing ladder ────────────────────────────────────────────
def outfit(temp_max: float, precip_mm: float, wind_kph: float) -> tuple[str, str]:
    rain  = precip_mm > 2
    windy = wind_kph  > 35

    if temp_max >= 27:
        base, icon = "Short shirt + Shorts", "🩳"
    elif temp_max >= 20:
        base, icon = "Short shirt + Long pants", "👖"
    elif temp_max >= 13:
        base, icon = "Long shirt + Light coat", "🧥"
    elif temp_max >= 5:
        base, icon = "Long shirt + Heavy coat", "🧤"
    else:
        base, icon = "Thermals + Heavy coat + Boots", "❄️"

    if rain:
        base += " + Umbrella"
        icon  = "☂️"
    elif windy and temp_max < 20:
        base += " + Windproof layer"

    return icon, base


# ── Weather summary ────────────────────────────────────────────
def weather_summary(w: dict) -> str:
    parts = [f"{w['temp_max']:.0f}°C"]
    if   w["precip_mm"] > 5: parts.append("rainy")
    elif w["precip_mm"] > 1: parts.append("light showers")
    if   w["wind_kph"]  > 50: parts.append("very windy")
    elif w["wind_kph"]  > 35: parts.append("windy")
    suffix = " · climate estimate" if w.get("proxy") else ""
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

city = st.text_input("Destination", value=ip_city(),
                     placeholder="e.g. Paris, Tokyo, New York…")

travel_date = st.date_input("Date", value=date.today())

go = st.button("Check What to Wear")

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
            st.error("Weather data unavailable. Try a different date.")
            st.stop()

    icon, directive = outfit(w["temp_max"], w["precip_mm"], w["wind_kph"])
    summary  = weather_summary(w)
    date_str = travel_date.strftime("%d %b %Y")

    st.markdown(f"""
    <div class="result-box">
      <div class="result-meta">📍 {loc['name']}, {loc['country']} · {date_str}</div>
      <div class="result-weather">{summary}</div>
      <div class="result-emoji">{icon}</div>
      <div class="result-outfit">{directive}</div>
    </div>
    """, unsafe_allow_html=True)
