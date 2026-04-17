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
# 凡例（復元済み）
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
☀️ 晴れ 🌤 くもり ☁️ 曇り  
🌧 雨 ❄️ 雪 ⛈ 雷  
""")

# =====================
# CSS（プロUI）
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
    box-shadow:0 2px 8px rgba(0,0,0,0.4);
}
.ok {border-left:6px solid #00ff88;}
.warn {border-left:6px solid orange;}
.ng {border-left:6px solid red;}
.small {font-size:12px;color:#aaa;}
</style>
""", unsafe_allow_html=True)

# =====================
# API SAFE
# =====================
def safe(url):
    try:
        r = requests.get(url, timeout=5)
        return r.json() if r.status_code == 200 else {}
    except:
        return {}
# ===== API =====
def safe(url):
    try:
        r = requests.get(url, timeout=5)
        return r.json() if r.status_code == 200 else {}
    except:
        return {}

# ★ここに入れる（重要）
@st.cache_data(ttl=300)
def get_place(lat, lon):
    try:
        url = (
            "https://api.openweathermap.org/geo/1.0/reverse"
            f"?lat={lat}&lon={lon}&limit=1&appid={API_KEY}"
        )
        data = safe(url)

        if isinstance(data, list) and len(data) > 0:
            d = data[0]

            return (
                d.get("local_names", {}).get("ja")
                or d.get("name")
                or "不明地点"
            )

    except:
        pass

    return "取得中..."
# =====================
# 🔥 地名（安定版：重要修正）
# =====================
def get_place(lat, lon):
    try:
        url = (
            "https://api.openweathermap.org/geo/1.0/reverse"
            f"?lat={lat}&lon={lon}&limit=1&appid={API_KEY}"
        )
        data = safe(url)

        # list保証
        if isinstance(data, list) and len(data) > 0:
            d = data[0]

            return (
                d.get("local_names", {}).get("ja")
                or d.get("name")
                or "不明地点"
            )

    except:
        pass

    # fallback（これが重要）
    return f"{lat:.3f}, {lon:.3f}"

# =====================
# Weather API
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

# =====================
# 判定
# =====================
def wind_class(w):
    if w > 8:
        return "ng"
    elif w > 5:
        return "warn"
    return "ok"

def drone(wind, gust):
    if gust > 10:
        return "🔴 飛行中止","ng"
    elif wind > 5 or gust > 8:
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

col1, col2 = st.columns([1,1])

# =====================
# MAP（クリック即更新）
# =====================
with col1:
    m = folium.Map(location=[lat, lon], zoom_start=10)

    folium.Marker([lat, lon], tooltip="現在地").add_to(m)

    map_data = st_folium(m, key="map", height=500)

    if map_data and map_data.get("last_clicked"):
        new_lat = map_data["last_clicked"]["lat"]
        new_lon = map_data["last_clicked"]["lng"]

        if new_lat != lat or new_lon != lon:
            st.session_state.lat = new_lat
            st.session_state.lon = new_lon
            st.rerun()

    # ★地名（ここ重要）
    st.markdown(f"### 📍 {get_place(lat, lon)}")

# =====================
# ===== 現在天気 =====
with col2:
    cur = get_current(lat, lon) or {}

    wind = cur.get("wind", {}).get("speed", 0)
    gust = cur.get("wind", {}).get("gust", wind * 1.5)
    temp = cur.get("main", {}).get("temp", 0)

    icon = cur.get("weather", [{}])[0].get("icon", "")
    icon_url = f"http://openweathermap.org/img/wn/{icon}@2x.png" if icon else "http://openweathermap.org/img/wn/01d@2x.png"

    pressure = cur.get("main", {}).get("pressure", None)
    pressure_txt = f"{pressure:.0f} hPa" if isinstance(pressure, (int, float)) else "--"

    status, cls = drone(wind, gust)

    st.markdown(f"""
    <div class="card {cls}">
        <img src="{icon_url}" width="80">
        <h2>{status}</h2>
        🌬 {wind:.1f} / ⚡ {gust:.1f}<br>
        🌡 {temp:.1f}℃<br>
        📉 {pressure_txt}
    </div>
    """, unsafe_allow_html=True)

# =====================
# FORECAST
# =====================
fc = get_forecast(lat, lon)

tab1, tab2 = st.tabs(["⏰ 時間予報", "📅 週間予報"])

# =====================
# 時間予報（完全復元）
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

        # 🔥 復元ポイント
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
# 週間予報（完全復元）
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
