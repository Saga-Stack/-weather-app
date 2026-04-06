import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import folium
from streamlit_folium import st_folium
from streamlit_autorefresh import st_autorefresh

API_KEY = "45313509cae2fb08083c689a0a9abbad"

st.set_page_config(layout="wide")
st.title("🌬 福島 天気＋風速＋気圧＋河川カメラ")

# ===== 凡例 =====
with st.expander("📘 マークの説明（凡例）"):
    st.markdown("""
🌤 天気：☀️晴れ / ☁️くもり / 🌧雨 / ❄️雪  
🌬 風速：平均風速  
⬆️ 最大風速 / ⬇️ 最小風速  
⚡ 突風率 = 最大 ÷ 平均（2以上で注意）  
📉 気圧：1000以下で低気圧 / 990以下で警戒  
""")

# ===== 自動更新 =====
st_autorefresh(interval=60 * 1000, key="refresh")

# ===== 地域（固定）=====
cities = {
    "福島市": (37.7608, 140.4747),
    "伊達市": (37.8167, 140.5000),
    "二本松市": (37.5833, 140.4333),
    "本宮市": (37.5167, 140.4000),
    "郡山市": (37.4005, 140.3597),
    "南相馬市": (37.6422, 140.9575),
    "相馬市": (37.8000, 140.9333),
    "浪江町": (37.4917, 141.0000),
}

# ===== API =====
def safe_request(url):
    try:
        return requests.get(url, timeout=5).json()
    except:
        return {}

@st.cache_data(ttl=300)
def get_current(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    return safe_request(url)

@st.cache_data(ttl=300)
def get_forecast(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    data = safe_request(url)

    if "list" not in data:
        return pd.DataFrame()

    rows = []
    for x in data["list"][:8]:
        rows.append({
            "time": datetime.fromtimestamp(x["dt"]),
            "wind": x["wind"]["speed"],
            "pressure": x["main"]["pressure"],
            "icon": x["weather"][0]["icon"]
        })
    return pd.DataFrame(rows)

# ===== 色 =====
def wind_color(w):
    return "#d0f0ff" if w < 3 else "#fff3b0" if w < 6 else "#ff9999"

def pressure_color(p):
    return "red" if p < 990 else "orange" if p < 1000 else "green"

# ===== カメラ =====
def get_camera_links(lat, lon):
    base = "https://www.river.go.jp/kawabou/pc/tm"
    return [
        f"{base}?zm=10&clat={lat}&clon={lon}",
        f"{base}?zm=13&clat={lat}&clon={lon}"
    ]

# ===== タブ =====
tab1, tab2 = st.tabs(["📍 地図", "🌤 予報"])

# ===== 地図 =====
with tab1:
    m = folium.Map(location=[37.6, 140.5], zoom_start=8)

    for city, (lat, lon) in cities.items():
        folium.Marker([lat, lon], tooltip=city).add_to(m)

    st_folium(m, width=700, height=500)

    selected_city = st.selectbox("地点", list(cities.keys()))

    lat, lon = cities[selected_city]
    current = get_current(lat, lon)

    if "weather" in current:
        p = current["main"]["pressure"]
        w = current["wind"]["speed"]

        st.markdown(f"<h1 style='color:{pressure_color(p)};'>📉 {p} hPa</h1>", unsafe_allow_html=True)
        st.write(f"🌬 {w} m/s")

    st.markdown(f"### 📷 {selected_city} 周辺カメラ")
    for i, link in enumerate(get_camera_links(lat, lon)):
        st.link_button(f"カメラ{i+1}", link)

# ===== 予報 =====
with tab2:
    lat, lon = cities[selected_city]
    df = get_forecast(lat, lon)

    if not df.empty:
        df["t"] = df["time"].dt.strftime("%H:%M")
        st.line_chart(df.set_index("t")["pressure"])

        html = "<div style='display:flex;overflow-x:auto;'>"

        for i, row in df.iterrows():
            window = df.iloc[max(0,i-2):min(len(df),i+3)]

            max_w = window["wind"].max()
            min_w = window["wind"].min()
            avg_w = window["wind"].mean()
            gust = max_w / avg_w if avg_w > 0 else 0

            html += f"""
            <div style="min-width:160px;background:{wind_color(max_w)};margin:5px;padding:10px;border-radius:10px;">
                <h4>{row['time'].strftime('%m/%d %H:%M')}</h4>
                <img src="http://openweathermap.org/img/wn/{row['icon']}@2x.png">
                <p>🌬 {avg_w:.1f}</p>
                <p>⬆️ {max_w:.1f}</p>
                <p>⬇️ {min_w:.1f}</p>
                <p>⚡ {gust:.1f}</p>
                <p>📉 {row['pressure']}</p>
            </div>
            """

        html += "</div>"
        st.components.v1.html(html, height=520)
