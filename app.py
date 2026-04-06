import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import folium
from streamlit_folium import st_folium
from streamlit_autorefresh import st_autorefresh

API_KEY = "45313509cae2fb08083c689a0a9abbad"

st.set_page_config(layout="wide")
st.title("🌬 福島県 天気＋風速＋河川カメラ（軽量版）")

# ===== 自動更新（軽量化）=====
st_autorefresh(interval=60 * 1000, key="refresh")

# ===== 市町村 =====
cities = {
    "福島市": (37.7608, 140.4747),
    "伊達市": (37.8167, 140.5000),
    "二本松市": (37.5833, 140.4333),
    "本宮市": (37.5167, 140.4000),
    "相馬市": (37.8000, 140.9333),
    "南相馬市": (37.6422, 140.9575),
    "浪江町": (37.4917, 141.0000),
    "只見町": (37.3500, 139.3167),
    "郡山市": (37.4005, 140.3597)
}

# ===== キャッシュ（最重要）=====
@st.cache_data(ttl=300)
def get_current(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    return requests.get(url).json()

@st.cache_data(ttl=300)
def get_forecast(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    data = requests.get(url).json()

    if "list" not in data:
        return pd.DataFrame()

    rows = []
    for x in data["list"][:8]:
        rows.append({
            "time": datetime.fromtimestamp(x["dt"]),
            "wind": x["wind"]["speed"],
            "weather": x["weather"][0]["main"],
            "icon": x["weather"][0]["icon"]
        })
    return pd.DataFrame(rows)

# ===== 天気 =====
weather_jp = {
    "Clear": "☀️ 晴れ",
    "Clouds": "☁️ くもり",
    "Rain": "🌧 雨",
    "Snow": "❄️ 雪"
}

# ===== 風背景 =====
def wind_color(w):
    if w < 3:
        return "linear-gradient(135deg,#aee,#dff)"
    elif w < 6:
        return "linear-gradient(135deg,#ffd27f,#ffe5b4)"
    else:
        return "linear-gradient(135deg,#ff8a8a,#ffb3b3)"

# ===== 河川カメラ =====
def get_camera_links(lat, lon):
    base = "https://www.river.go.jp/kawabou/pc/tm"
    return [
        f"{base}?zm=12&clat={lat}&clon={lon}",
        f"{base}?zm=13&clat={lat}&clon={lon}",
        f"{base}?zm=14&clat={lat}&clon={lon}"
    ]

# ===== 曜日 =====
week = ["月","火","水","木","金","土","日"]

# ===== タブ =====
tab1, tab2 = st.tabs(["📍 地図", "🌤 予報"])

# ===== 地図（固定化）=====
with tab1:
    if "map" not in st.session_state:
        st.session_state.map = folium.Map(location=[37.5, 140.5], zoom_start=8)
        for city, (lat, lon) in cities.items():
            folium.Marker([lat, lon], tooltip=city).add_to(st.session_state.map)

    m = st.session_state.map
    map_data = st_folium(m, width=700, height=500)

    selected_city = "福島市"

    if map_data and map_data.get("last_object_clicked"):
        lat_clicked = map_data["last_object_clicked"]["lat"]
        lon_clicked = map_data["last_object_clicked"]["lng"]

        min_dist = 999
        for city, (lat, lon) in cities.items():
            d = (lat - lat_clicked)**2 + (lon - lon_clicked)**2
            if d < min_dist:
                min_dist = d
                selected_city = city

    selected_city = st.selectbox("市町村", list(cities.keys()))

    lat, lon = cities[selected_city]
    current = get_current(lat, lon)

    if "weather" in current:
        jp = weather_jp.get(current["weather"][0]["main"], "")

        st.markdown(f"""
        <div style="background:#eef;border-radius:15px;padding:15px;width:250px;text-align:center;">
            <h3>📍 {selected_city}</h3>
            <img src="http://openweathermap.org/img/wn/{current['weather'][0]['icon']}@2x.png">
            <p>{jp}</p>
            <p style="font-size:20px;">🌬 {current['wind']['speed']} m/s</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### 📷 河川カメラ")
    links = get_camera_links(lat, lon)

    for i, link in enumerate(links):
        st.link_button(f"カメラ{i+1}", link)

# ===== 予報 =====
with tab2:
    lat, lon = cities[selected_city]
    df = get_forecast(lat, lon)

    st.subheader(f"{selected_city} の3時間予報")

    if not df.empty:
        html = """
        <style>
        @keyframes blink {
            0% {opacity:1;}
            50% {opacity:0.3;}
            100% {opacity:1;}
        }
        </style>
        <div style="display:flex; overflow-x:auto; gap:16px; padding:12px; align-items:stretch;">
        """

        for i, row in df.iterrows():
            jp = weather_jp.get(row["weather"], row["weather"])

            w = week[row["time"].weekday()]
            label = row["time"].strftime(f"%m/%d({w}) %H:%M")

            window = df.iloc[max(0, i-2):min(len(df), i+3)]

            max_w = float(window["wind"].max())
            min_w = float(window["wind"].min())
            avg_w = float(window["wind"].mean())

            gust_ratio = max_w / avg_w if avg_w > 0 else 0.0

            gust_style = ""
            blink_style = ""

            if gust_ratio >= 2.5:
                gust_style = "color:red;font-weight:bold;"
                blink_style = "animation: blink 1s infinite;"
            elif gust_ratio >= 1.8:
                gust_style = "color:orange;"

            bg = wind_color(max_w)

            html += f"""
            <div style="
                min-width:180px;
                min-height:260px;
                background:{bg};
                border-radius:18px;
                padding:12px;
                text-align:center;
                display:flex;
                flex-direction:column;
                justify-content:space-between;
                {blink_style}
            ">
                <div>
                    <h3>{label}</h3>
                    <img src="http://openweathermap.org/img/wn/{row['icon']}@2x.png">
                    <p>{jp}</p>
                </div>

                <div>
                    <p>🌬 {avg_w:.1f} m/s</p>
                    <p>⬆️ {max_w:.1f} m/s</p>
                    <p>⬇️ {min_w:.1f} m/s</p>
                    <p style="{gust_style}">⚡ {gust_ratio:.1f}倍</p>
                </div>
            </div>
            """

        html += "</div>"
        st.components.v1.html(html, height=550, scrolling=True)