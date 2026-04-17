import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import folium
from streamlit_folium import st_folium

# ===== API =====
API_KEY = st.secrets["OPENWEATHER_API_KEY"]

st.set_page_config(layout="wide")
st.title("そらのめ")

# ===== 凡例 =====
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
☀️ 晴れ  
🌤 晴れ時々くもり  
☁️ くもり  
🌫 霧  
🌦 弱い雨  
🌧 雨  
❄️ 雪  
⛈ 雷・激しい雨  
❓ 不明  
""")

# ===== CSS =====
st.markdown("""
<style>
.card {
    background:#1e1e1e;
    color:white;
    padding:12px;
    border-radius:12px;
    margin:6px;
    text-align:center;
}
.ok {border-left:6px solid #00ff88;}
.warn {border-left:6px solid orange;}
.ng {border-left:6px solid red;}
.small {font-size:12px;color:#aaa;}
</style>
""", unsafe_allow_html=True)

# ===== API =====
def safe(url):
    try:
        r = requests.get(url, timeout=5)
        return r.json() if r.status_code == 200 else {}
    except:
        return {}

# ===== ★安定版 geocode（キャッシュ付き・座標出さない）=====
@st.cache_data(ttl=3600)
def get_place(lat, lon):
    try:
        # ===== OpenWeather =====
        url1 = (
            "http://api.openweathermap.org/geo/1.0/reverse"
            f"?lat={lat}&lon={lon}&limit=1&appid={API_KEY}"
        )
        data1 = requests.get(url1, timeout=3).json()

        if isinstance(data1, list) and data1:
            p = data1[0]
            name = p.get("local_names", {}).get("ja") or p.get("name")
            if name:
                return name

        # ===== Nominatim（安定）=====
        url2 = (
            "https://nominatim.openstreetmap.org/reverse"
            f"?format=json&lat={lat}&lon={lon}&zoom=12&accept-language=ja"
        )

        headers = {"User-Agent": "streamlit-app"}
        data2 = requests.get(url2, headers=headers, timeout=5).json()

        if "address" in data2:
            addr = data2["address"]
            return (
                addr.get("city")
                or addr.get("town")
                or addr.get("village")
                or addr.get("county")
                or addr.get("state")
                or "不明地点"
            )

    except:
        pass

    # ★本質改善：座標は出さない
    return "不明地点"


def get_current(lat, lon):
    return safe(
        f"https://api.openweathermap.org/data/2.5/weather?"
        f"lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    )

def get_forecast(lat, lon):
    return safe(
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&hourly=windspeed_10m,pressure_msl,weathercode"
        f"&daily=temperature_2m_max,temperature_2m_min,windspeed_10m_max,weathercode"
        f"&forecast_days=14&timezone=Asia%2FTokyo"
    )

# ===== 天気 =====
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
    if w is None: return ""
    if w > 8: return "ng"
    if w > 5: return "warn"
    return "ok"

def drone(wind, gust):
    if gust > 10:
        return "🔴 飛行中止","ng"
    if wind > 5 or gust > 8:
        return "🟡 注意","warn"
    return "🟢 飛行可能","ok"

# ===== 初期位置 =====
if "lat" not in st.session_state:
    st.session_state.lat = 37.76
    st.session_state.lon = 140.47

lat = st.session_state.lat
lon = st.session_state.lon

col1, col2 = st.columns(2)

# ===== 地図 =====
with col1:
    m = folium.Map(location=[lat, lon], zoom_start=11)

    folium.Marker(
        [lat, lon],
        tooltip="選択地点",
        icon=folium.Icon(color="red")
    ).add_to(m)

    map_data = st_folium(m, key="map", width=700, height=500)

    if map_data and map_data.get("last_clicked"):
        new_lat = map_data["last_clicked"]["lat"]
        new_lon = map_data["last_clicked"]["lng"]

        if new_lat != st.session_state.lat or new_lon != st.session_state.lon:
            st.session_state.lat = new_lat
            st.session_state.lon = new_lon
            st.rerun()

    st.markdown(f"### 📍 {get_place(lat, lon)}")

# ===== 現在天気 =====
with col2:
    cur = get_current(lat, lon)

    if cur and "weather" in cur:
        wind = cur.get("wind", {}).get("speed", 0)
        gust = cur.get("wind", {}).get("gust", wind * 1.5)
        temp = cur.get("main", {}).get("temp", 0)

        icon = cur.get("weather", [{}])[0].get("icon", "")
        icon_url = f"http://openweathermap.org/img/wn/{icon}@2x.png"

        pressure = cur.get("main", {}).get("pressure", None)
        pressure_txt = f"{pressure:.0f} hPa" if isinstance(pressure, (int, float)) else "--"

        status, cls = drone(wind, gust)

        st.markdown(f"""
        <div class="card {cls}">
        <img src="{icon_url}" style="width:80px;">
        <h2>{status}</h2>
        🌬 {wind:.1f} / ⚡ {gust:.1f}<br>
        🌡 {temp:.1f}℃<br>
        📉 {pressure_txt}
        </div>
        """, unsafe_allow_html=True)

# ===== 予報 =====
fc = get_forecast(lat, lon)

tab1, tab2 = st.tabs(["⏰ 時間予報", "📅 週間予報"])

with tab1:
    view = st.radio("表示時間", ["12時間","24時間","48時間"], horizontal=True)
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
        df["pressure"] = df["pressure"].where(df["pressure"] < 2000)
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

with tab2:
    if "daily" in fc:
        df2 = pd.DataFrame({
            "date": pd.to_datetime(fc["daily"]["time"]),
            "tmax": fc["daily"]["temperature_2m_max"],
            "tmin": fc["daily"]["temperature_2m_min"],
            "wind": fc["daily"]["windspeed_10m_max"],
            "weather": fc["daily"]["weathercode"]
        }).head(14)

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
