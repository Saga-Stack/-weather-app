import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import folium
from streamlit_folium import st_folium
from streamlit_autorefresh import st_autorefresh

API_KEY = "45313509cae2fb08083c689a0a9abbad"

st.set_page_config(layout="wide")
st.title("🌬 福島県 天気＋風速＋気圧＋河川カメラ（完全版）")

# ===== 自動更新 =====
st_autorefresh(interval=60 * 1000, key="refresh")

# ===== 初期都市 =====
base_cities = {
    "福島市": (37.7608, 140.4747),
    "郡山市": (37.4005, 140.3597),
    "相馬市": (37.8000, 140.9333),
}

# ===== セッション =====
if "dynamic_cities" not in st.session_state:
    st.session_state.dynamic_cities = {}

if "selected_city" not in st.session_state:
    st.session_state.selected_city = "福島市"

# ===== API安全化 =====
def safe_request(url):
    try:
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        return res.json()
    except:
        return {}

# ===== 天気取得 =====
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
    for x in data["list"][:6]:
        rows.append({
            "time": datetime.fromtimestamp(x["dt"]),
            "wind": x["wind"]["speed"],
            "pressure": x["main"]["pressure"],  # ★追加
            "weather": x["weather"][0]["main"],
            "icon": x["weather"][0]["icon"]
        })
    return pd.DataFrame(rows)

# ===== ジオコーディング =====
@st.cache_data(ttl=3600)
def geocode(query):
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={query}&limit=1&appid={API_KEY}"
    data = safe_request(url)
    if len(data) > 0:
        return data[0]["lat"], data[0]["lon"], data[0]["name"]
    return None, None, None

# ===== UI（検索）=====
search_query = st.text_input("🔍 地名で検索（例：東京、仙台）")

if search_query:
    lat, lon, name = geocode(search_query)
    if lat:
        st.session_state.dynamic_cities[name] = (lat, lon)
        st.session_state.selected_city = name
    else:
        st.warning("場所が見つかりませんでした")

# ===== 都市統合 =====
all_cities = {**base_cities, **st.session_state.dynamic_cities}

# ===== 天気日本語 =====
weather_jp = {
    "Clear": "☀️ 晴れ",
    "Clouds": "☁️ くもり",
    "Rain": "🌧 雨",
    "Snow": "❄️ 雪"
}

# ===== 色設定 =====
def wind_color(w):
    if w < 2:
        return "#d0f0ff"
    elif w < 5:
        return "#fff3b0"
    elif w < 8:
        return "#ffcc99"
    else:
        return "#ff9999"

def pressure_alert(p):
    if p < 990:
        return "🚨 強い低気圧（警戒）"
    elif p < 1000:
        return "⚠ 低気圧（注意）"
    return ""

# ===== カメラ =====
def get_camera_links(lat, lon):
    base = "https://www.river.go.jp/kawabou/pc/tm"
    return [
        f"{base}?zm=12&clat={lat}&clon={lon}",
        f"{base}?zm=13&clat={lat}&clon={lon}",
        f"{base}?zm=14&clat={lat}&clon={lon}"
    ]

week = ["月","火","水","木","金","土","日"]

# ===== タブ =====
tab1, tab2 = st.tabs(["📍 地図", "🌤 予報"])

# ===== 地図 =====
with tab1:

    m = folium.Map(location=[37.5, 140.5], zoom_start=7)

    for city, (lat, lon) in all_cities.items():
        folium.Marker([lat, lon], tooltip=city).add_to(m)

    map_data = st_folium(m, width=700, height=500)

    # 地図クリック
    if map_data and map_data.get("last_object_clicked"):
        lat_clicked = map_data["last_object_clicked"]["lat"]
        lon_clicked = map_data["last_object_clicked"]["lng"]

        min_dist = 999
        for city, (lat, lon) in all_cities.items():
            d = (lat - lat_clicked)**2 + (lon - lon_clicked)**2
            if d < min_dist:
                min_dist = d
                st.session_state.selected_city = city

    selected_city = st.selectbox(
        "市町村",
        list(all_cities.keys()),
        index=list(all_cities.keys()).index(st.session_state.selected_city)
    )

    st.session_state.selected_city = selected_city

    lat, lon = all_cities[selected_city]
    current = get_current(lat, lon)

    if "weather" in current:

        pressure = current["main"]["pressure"]
        wind = current["wind"]["speed"]
        jp = weather_jp.get(current["weather"][0]["main"], "")

        st.markdown(f"""
        <div style="background:#eef;border-radius:15px;padding:15px;width:260px;text-align:center;">
            <h3>📍 {selected_city}</h3>
            <img src="http://openweathermap.org/img/wn/{current['weather'][0]['icon']}@2x.png">
            <p>{jp}</p>
            <p>🌬 {wind} m/s</p>
            <p>📉 {pressure} hPa</p>
        </div>
        """, unsafe_allow_html=True)

        # ===== アラート =====
        alert = pressure_alert(pressure)

        if alert:
            st.error(alert)

        if pressure < 1000 and wind > 8:
            st.error("🚨 低気圧＋強風 → 荒天警戒")

    # ===== カメラ =====
    st.markdown("### 📷 河川カメラ")
    links = get_camera_links(lat, lon)
    for i, link in enumerate(links):
        st.markdown(f"[📷 カメラ{i+1}]({link})")

# ===== 予報 =====
with tab2:

    lat, lon = all_cities[st.session_state.selected_city]
    df = get_forecast(lat, lon)

    st.subheader(f"{st.session_state.selected_city} の3時間予報")

    if not df.empty:

        html = '<div style="display:flex; overflow-x:auto; gap:12px; padding:10px;">'

        for i, row in df.iterrows():

            jp = weather_jp.get(row["weather"], row["weather"])

            w = week[row["time"].weekday()]
            label = row["time"].strftime(f"%m/%d({w}) %H:%M")

            window = df.iloc[max(0, i-2):min(len(df), i+3)]

            max_w = float(window["wind"].max())
            min_w = float(window["wind"].min())
            avg_w = float(window["wind"].mean())

            gust_ratio = max_w / avg_w if avg_w > 0 else 0

            bg = wind_color(max_w)
            alert_color = "red" if row["pressure"] < 1000 else "black"

            html += f"""
            <div style="
                min-width:170px;
                background:{bg};
                border-radius:15px;
                padding:10px;
                text-align:center;
            ">
                <h4>{label}</h4>
                <img src="http://openweathermap.org/img/wn/{row['icon']}@2x.png">
                <p>{jp}</p>
                <p>🌬 {avg_w:.1f}</p>
                <p>📉 <span style="color:{alert_color}">{row['pressure']} hPa</span></p>
                <p>⚡ {gust_ratio:.1f}</p>
            </div>
            """

        html += "</div>"
        st.components.v1.html(html, height=500, scrolling=True)
