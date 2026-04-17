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

---

### 🧠 補足
・突風率が高い = 急な風変化あり  
・風速5m/s以上で注意  
・突風10m/s以上は飛行NG  
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
# ===== API =====
def get_place(lat, lon):
    try:
        data = requests.get(
            f"http://api.openweathermap.org/geo/1.0/reverse?"
            f"lat={lat}&lon={lon}&limit=1&appid={API_KEY}"
        ).json()

        if data:
            return data[0].get("local_names", {}).get("ja", data[0]["name"])
    except:
        pass

    return "福島市"


def safe(url):
    try:
        r = requests.get(url, timeout=5)
        return r.json() if r.status_code == 200 else {}
    except:
        return {}

def get_current(lat, lon):
    return safe(f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric")

def get_forecast(lat, lon):
    return safe(
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&hourly=windspeed_10m,pressure_msl,weathercode"
        f"&daily=temperature_2m_max,temperature_2m_min,windspeed_10m_max,weathercode"
        f"&forecast_days=14"
        f"&timezone=Asia%2FTokyo"
    )

# ===== 天気コード =====
def weather_icon(code):
    if code == 0: return "☀️"
    elif code in [1,2]: return "🌤"
    elif code == 3: return "☁️"
    elif code in [45,48]: return "🌫"
    elif code in [51,53,55]: return "🌦"
    elif code in [61,63,65]: return "🌧"
    elif code in [71,73,75]: return "❄️"
    elif code in [95,96,99]: return "⛈"
    else: return "❓"

# ===== 判定 =====
def wind_class(w):
    if w is None: return ""
    if w > 8: return "ng"
    elif w > 5: return "warn"
    else: return "ok"

def drone(wind, gust):
    if gust > 10:
        return "🔴 飛行中止","ng"
    elif wind > 5 or gust > 8:
        return "🟡 注意","warn"
    else:
        return "🟢 飛行可能","ok"

# ===== 時刻 =====
def fmt(dt):
    dt = pd.to_datetime(dt)
    now = datetime.now()

    hour = dt.hour
    ampm = "午前" if hour < 12 else "午後"
    h = hour % 12 or 12

    label = f"{ampm}{h}時"

    if dt.date() == now.date():
        return f"今日 {label}"
    elif dt.date() == now.date() + timedelta(days=1):
        return f"明日 {label}"
    else:
        return dt.strftime("%m/%d ") + label

# ===== 初期位置 =====
lat, lon = 37.76, 140.47

col1, col2 = st.columns([2,1])

# ===== 地図 =====
with col1:
    m = folium.Map(location=[lat, lon], zoom_start=8)
    folium.Marker([lat, lon]).add_to(m)  # ← 追加（現在地点表示）

    map_data = st_folium(m, width=700, height=500)

    if map_data and map_data.get("last_clicked"):
        lat = map_data["last_clicked"]["lat"]
        lon = map_data["last_clicked"]["lng"]

    # 🔥 地名表示（これが本体）
    st.markdown(f"### 📍 {get_place(lat, lon)}")
# ===== 現在 =====
with col2:
    cur = get_current(lat, lon)

    if "weather" in cur:
        wind = cur.get("wind", {}).get("speed", 0)
        gust = cur.get("wind", {}).get("gust", wind * 1.5)
        temp = cur.get("main", {}).get("temp", 0)

        icon = cur.get("weather", [{}])[0].get("icon", "")
        icon_url = f"http://openweathermap.org/img/wn/{icon}@2x.png"

        # 気圧修正
        pressure_raw = cur.get("main", {}).get("pressure", None)
        try:
            pressure = float(pressure_raw)
        except:
            pressure = None

        if pressure is None or pressure < 800 or pressure > 1100:
            pressure_txt = "--"
        else:
            pressure_txt = f"{pressure:.0f} hPa"

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

# ===== 時間 =====
with tab1:
    view = st.radio("表示時間", ["12時間", "24時間", "48時間"], horizontal=True)
    hours_map = {"12時間":12, "24時間":24, "48時間":48}
    limit = hours_map[view]

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
        df["ratio"] = df.apply(lambda x: x["max"]/x["wind"] if x["wind"] > 0 else 0, axis=1)

        df = df.bfill().ffill()
        df["pressure"] = df["pressure"].apply(lambda x: x if x < 2000 else None)

        df["date"] = df["time"].dt.date

        for d, g in df.groupby("date"):
            st.subheader(str(d))
            cols = st.columns(3)

            for i, (_, r) in enumerate(g.iterrows()):
                cls = wind_class(r["wind"])
                pressure_txt = f"{r['pressure']:.0f} hPa" if pd.notna(r["pressure"]) else "--"

                with cols[i % 3]:
                    st.markdown(f"""
                    <div class="card {cls}">
                    {weather_icon(r['weather'])}<br>
                    <b>{fmt(r['time'])}</b><br>
                    🌬 {r['wind']:.1f}<br>
                    ⬆️ {r['max']:.1f}<br>
                    ⬇️ {r['min']:.1f}<br>
                    ⚡ {r['ratio']:.1f}<br>
                    <div class="small">📉 {pressure_txt}</div>
                    </div>
                    """, unsafe_allow_html=True)

# ===== 週間 =====
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
            cls = wind_class(r["wind"])

            with cols[i % 4]:
                st.markdown(f"""
                <div class="card {cls}">
                {weather_icon(r['weather'])}<br>
                <b>{r['date'].strftime('%m/%d')}</b><br>
                🌡 {r['tmax']:.0f}/{r['tmin']:.0f}<br>
                🌬 {r['wind']:.1f}
                </div>
                """, unsafe_allow_html=True)
