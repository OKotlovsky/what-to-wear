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

# ── CSS: full-screen centered card, iOS feel ───────────────────
st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

*, html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, sans-serif !important;
    box-sizing: border-box;
}

/* Hide all Streamlit chrome */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"] { display: none !important; }

/* Full-viewport centering */
.stApp {
    background: #f0f2f5;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
}

/* Tight single-screen container */
.block-container {
    padding: 1.5rem 1.2rem !important;
    max-width: 360px !important;
    margin: auto !important;
    width: 100% !important;
}

/* White card wrapping everything */
section[data-testid="stVerticalBlock"] > div:first-child {
    background: white;
    border-radius: 28px;
    padding: 2rem 1.6rem 1.8rem;
    box-shadow: 0 8px 32px rgba(0,0,0,0.10);
}

/* App title */
.app-title {
    text-align: center;
    font-size: 1.25rem;
    font-weight: 800;
    color: #1a1a2e;
    margin-bottom: 1.4rem;
    letter-spacing: -0.02em;
}

/* Input labels */
label[data-testid="stWidgetLabel"] p {
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.07em !important;
    text-transform: uppercase !important;
    color: #8b9ab1 !important;
    margin-bottom: 2px !important;
}

/* Text input */
[data-testid="stTextInput"] input {
    border-radius: 12px !important;
    border: 1.5px solid #e5e9f0 !important;
    font-size: 1rem !important;
    padding: 0.6rem 0.85rem !important;
    color: #1a1a2e !important;
    background: #fafbfc !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #667eea !important;
    box-shadow: 0 0 0 3px rgba(102,126,234,0.15) !important;
}

/* Date input */
[data-testid="stDateInput"] input {
    border-radius: 12px !important;
    border: 1.5px solid #e5e9f0 !important;
    font-size: 1rem !important;
    padding: 0.6rem 0.85rem !important;
    color: #1a1a2e !important;
    background: #fafbfc !important;
}

/* CTA button */
.stButton > button {
    width: 100% !important;
    border-radius: 14px !important;
    background: linear-gradient(135deg, #667eea, #764ba2) !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 0.78rem !important;
    border: none !important;
    margin-top: 0.6rem !important;
    box-shadow: 0 4px 18px rgba(102,126,234,0.38) !important;
    letter-spacing: 0.01em;
    transition: opacity 0.15s;
}
.stButton > button:active { opacity: 0.85; }

/* Result block */
.result-box {
    margin-top: 1.3rem;
    background: #f7f8fc;
    border-radius: 18px;
    padding: 1.1rem 1.2rem 1rem;
    text-align: center;
    border: 1.5px solid #e8eaf2;
}
.result-meta {
    font-size: 0.78rem;
    font-weight: 600;
    color: #8b9ab1;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-bottom: 0.4rem;
}
.result-weather {
    font-size: 0.95rem;
    color: #4a5568;
    margin-bottom: 0.55rem;
}
.result-outfit {
    font-size: 1.35rem;
    font-weight: 800;
    color: #1a1a2e;
    letter-spacing: -0.02em;
    line-height: 1.25;
}
.result-emoji { font-size: 2rem; margin-bottom: 0.3rem; }
</style>
""", unsafe_allow_html=True)


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
    from datetime import date as _date
    today = _date.today()
    delta = (day - today).days
    base  = {"latitude": lat, "longitude": lon, "timezone": "auto",
             "daily": "temperature_2m_max,temperature_2m_min,"
                      "precipitation_sum,windspeed_10m_max"}

    if -365 <= delta <= 16:
        url   = ("https://api.open-meteo.com/v1/forecast" if delta >= 0
                 else "https://archive-api.open-meteo.com/v1/archive")
        s = e = day
    else:
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
    rain  = precip_mm > 2

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
        icon = "🧥"
    else:
        base = "Thermals + Heavy coat"
        icon = "❄️"

    if rain:
        base += " + Umbrella"
        icon  = "☂️"

    return icon, base


# ── Weather summary sentence ───────────────────────────────────
def weather_summary(w: dict) -> str:
    t   = f"{w['temp_max']:.0f}°C"
    p   = w["precip_mm"]
    spd = w["wind_kph"]

    parts = [t]
    if p > 5:    parts.append("rainy")
    elif p > 1:  parts.append("light showers")
    if spd > 35: parts.append("windy")

    suffix = ""
    return " and ".join(parts) + suffix


# ── Default city from IP ───────────────────────────────────────
@st.cache_data(ttl=3600)
def ip_city() -> str:
    try:
        return requests.get("http://ip-api.com/json/?fields=city",
                            timeout=3).json().get("city", "Seattle")
    except Exception:
        return "Seattle"


# ══════════════════════════════════════════════
#  UI
# ══════════════════════════════════════════════
st.markdown('<div class="app-title">👗 What to Wear?</div>', unsafe_allow_html=True)

city = st.text_input("Destination", value=ip_city(), label_visibility="visible",
                     placeholder="e.g. Seattle, Tokyo, Paris…")

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
            st.error("Weather data unavailable.")
            st.stop()

    icon, directive = outfit(w["temp_max"], w["precip_mm"], w["wind_kph"])
    summary         = weather_summary(w)
    date_str        = travel_date.strftime("%d %b")

    st.markdown(f"""
    <div class="result-box">
      <div class="result-meta">📍 {loc['name']} · {date_str}</div>
      <div class="result-weather">{summary}</div>
      <div class="result-emoji">{icon}</div>
      <div class="result-outfit">{directive}</div>
    </div>
    """, unsafe_allow_html=True)
