import streamlit as st
import requests
from datetime import date

# ── Page config ────────────────────────────────────────────────
st.set_page_config(
    page_title="What to Wear",
    page_icon="👗",
    layout="centered"
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

    return " and ".join(parts)

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
st.title("👗 What to Wear?")

city = st.text_input("Destination", value=ip_city(), placeholder="e.g. Seattle, Tokyo...")
travel_date = st.date_input("Date", value=date.today())
go = st.button("Check What to Wear")

# ── Result (only shown after button press) ─────────────────────
if go:
    if not city.strip():
        st.error("Please enter a destination.")
        st.stop()

    with st.spinner("Fetching weather..."):
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

    st.write("---")
    st.subheader(f"📍 {loc['name']} · {date_str}")
    st.write(f"**Weather:** {summary}")
    st.write(f"**Recommendation:** {icon} {directive}")
