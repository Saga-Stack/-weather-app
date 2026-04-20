import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import folium
from streamlit_folium import st_folium

# =====================
# API KEY
# =====================
API_KEY = st.secrets["OPENWEATHER_API_KEY"]

st.set_page_config(layout="wide")
st.title("そらのめ PRO")

# =====================
# 凡例
# =====================
with st.expander("📘 凡例"):
    st.markdown("""
### 🚁 飛行判定
🟢 飛行可能  
🟡 注意  
🔴 飛行中止  

---

### 🌬 風データ
🌬 平均風速  
⬆️ 最大風速  
⬇️ 最小風速  
⚡ 突風率（最大 ÷ 平均）  

---

### 📉 気圧
1000hPa未満 → 不安定  
990hPa未満 → 低気圧（注意）  

---

### 🌤 天気マーク
☀️ 🌤 ☁️ 🌧 ❄️ ⛈
""")

# =====================
# CSS
# =====================
st.markdown("""
<style>
.card {
    background:#1e1e1e;
    color:white;
    padding:12px;
    border-radius:14px;
    margin:6px;
    text-align:center;
}
.ok {border-left:6px solid #00ff88;}
.warn {border-left:6px solid orange;}
.ng {border-left:6px solid red;}
</style>
""", unsafe_allow_html=True)

# =====================
# SAFE API
# =====================
def safe(url):
    try:
        headers = {"User-Agent": "soranome-app"}  # ←OSM対策追加
        r = requests.get(url, timeout=5, headers=headers)
        return r.json() if r.status_code == 200 else {}
    except:
        return {}

# =====================
# 🔥 地名（OSM版に差し替え）
# =====================
@st.cache_data(ttl=300)
def get_place(lat, lon):
    try:
        url = (
            "https://nominatim.openstreetmap.org/reverse"
            f"?lat={lat}&lon={lon}&format=json&accept-language=ja"
        )
        data = safe(url)

        return data.get("display_name", "不明地点")

    except:
        return "不明地点"

# =====================
# WEATHER
# =====================
def get_current(lat, lon):
    return safe(
        f"https://api.openweathermap.org/data/2.5/weather?"
        f"lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    )

def get_forecast(lat, lon):
    return safe(
        "https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        "&hourly=windspeed_10m,pressure_msl,weathercode"
        "&daily=temperature_2m_max,temperature_2m_min,windspeed_10m_max,weathercode"
        "&forecast_days=14&timezone=Asia%2FTokyo"
    )

# =====================
# ICON
# =====================
def weather_icon(code):
    return {
        0:"☀️",1:"🌤",2:"🌤",3:"☁️",
        45:"🌫",48:"🌫",
        51:"🌦",53:"🌦",55:"🌦",
        61:"🌧",63:"🌧",65:"🌧",
        71:"❄️",73:"❄️",75:"❄️",
        95:"⛈",96:"⛈",99:"⛈"
    }.get(code, "❓")

def wind_class(w):
    if w > 8: return "ng"
    if w > 5: return "warn"
    return "ok"

def drone(wind, gust):
    if gust > 10:
        return "🔴 飛行中止","ng"
    if wind > 5 or gust > 8:
        return "🟡 注意","warn"
    return "🟢 飛行可能","ok"

# =====================
# STATE
# =====================
if "lat" not in st.session_state:
    st.session_state.lat = 37.76
    st.session_state.lon = 140.47

lat = st.session_state.lat
lon = st.session_state.lon

col1, col2 = st.columns(2)

# =====================
# MAP
# =====================
with col1:
    m = folium.Map(location=[lat, lon], zoom_start=10)
    folium.Marker([lat, lon]).add_to(m)

    map_data = st_folium(m, key="map", height=500)

    if map_data and map_data.get("last_clicked"):
        new_lat = map_data["last_clicked"]["lat"]
        new_lon = map_data["last_clicked"]["lng"]

        if new_lat != lat or new_lon != lon:
            st.session_state.lat = new_lat
            st.session_state.lon = new_lon
            st.rerun()

    st.markdown(f"### 📍 {get_place(lat, lon)}")

# =====================
# CURRENT WEATHER
# =====================
with col2:
    cur = get_current(lat, lon) or {}

    wind = cur.get("wind", {}).get("speed", 0)
    gust = cur.get("wind", {}).get("gust", wind * 1.5)
    temp = cur.get("main", {}).get("temp", 0)

    icon = cur.get("weather", [{}])[0].get("icon", "")
    icon_url = f"http://openweathermap.org/img/wn/{icon}@2x.png" if icon else "http://openweathermap.org/img/wn/01d@2x.png"

    status, cls = drone(wind, gust)

    st.markdown(f"""
    <div class="card {cls}">
        <img src="{icon_url}" width="80">
        <h2>{status}</h2>
        🌬 {wind:.1f} / ⚡ {gust:.1f}<br>
        🌡 {temp:.1f}℃
    </div>
    """, unsafe_allow_html=True)

# =====================
# FORECAST
# =====================
fc = get_forecast(lat, lon)

tab1, tab2 = st.tabs(["⏰ 時間予報", "📅 週間予報"])

# =====================
# 時間
# =====================
with tab1:
    view = st.radio("表示", ["12時間","24時間","48時間"], horizontal=True)
    limit = {"12時間":12,"24時間":24,"48時間":48}[view]

    if "hourly" in fc:
        df = pd.DataFrame({
            "time": pd.to_datetime(fc["hourly"]["time"]),
            "wind": fc["hourly"]["windspeed_10m"],
            "pressure": fc["hourly"]["pressure_msl"],
            "weather": fc["hourly"]["weathercode"]
        })

        now = pd.Timestamp.now().floor("h")
        idx = (df["time"] - now).abs().idxmin()
        df = df.iloc[idx: idx + limit]

        df["max"] = df["wind"].rolling(3, center=True).max()
        df["min"] = df["wind"].rolling(3, center=True).min()
        df["ratio"] = df["max"] / df["wind"].replace(0, 1)

        df = df.bfill().ffill()
        df["date"] = df["time"].dt.date

        for d, g in df.groupby("date"):
            st.subheader(str(d))
            cols = st.columns(3)

            for i, (_, r) in enumerate(g.iterrows()):
                with cols[i % 3]:
                    st.markdown(f"""
                    <div class="card {wind_class(r['wind'])}">
                    {weather_icon(r['weather'])}<br>
                    <b>{r['time'].strftime('%H:%M')}</b><br>
                    🌬 {r['wind']:.1f}<br>
                    ⬆️ {r['max']:.1f}<br>
                    ⬇️ {r['min']:.1f}<br>
                    ⚡ {r['ratio']:.1f}<br>
                    </div>
                    """, unsafe_allow_html=True)

# =====================
# 週間
# =====================
with tab2:
    if "daily" in fc:
        df2 = pd.DataFrame({
            "date": pd.to_datetime(fc["daily"]["time"]),
            "tmax": fc["daily"]["temperature_2m_max"],
            "tmin": fc["daily"]["temperature_2m_min"],
            "wind": fc["daily"]["windspeed_10m_max"],
            "weather": fc["daily"]["weathercode"]
        })

        cols = st.columns(4)

        for i, (_, r) in enumerate(df2.iterrows()):
            with cols[i % 4]:
                st.markdown(f"""
                <div class="card {wind_class(r['wind'])}">
                {weather_icon(r['weather'])}<br>
                <b>{r['date'].strftime('%m/%d')}</b><br>
                🌡 {r['tmax']:.0f}/{r['tmin']:.0f}<br>
                🌬 {r['wind']:.1f}
                </div>
                """, unsafe_allow_html=True)
