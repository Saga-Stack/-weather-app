import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import folium
from streamlit_folium import st_folium
from streamlit_autorefresh import st_autorefresh

API_KEY = "45313509cae2fb08083c689a0a9abbad"

st.set_page_config(layout="wide")
st.title("そらのめ")

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

# ===== 福島県全市町村 =====
cities = {
    "福島市": (37.7608, 140.4747), "会津若松市": (37.4947, 139.9294),
    "郡山市": (37.4005, 140.3597), "白河市": (37.1260, 140.2107),
    "須賀川市": (37.2863, 140.3726), "喜多方市": (37.6505, 139.8736),
    "相馬市": (37.8000, 140.9333), "二本松市": (37.5833, 140.4333),
    "田村市": (37.4333, 140.5833), "南相馬市": (37.6422, 140.9575),
    "伊達市": (37.8167, 140.5000), "本宮市": (37.5167, 140.4000),

    "桑折町": (37.8500, 140.5167), "国見町": (37.8833, 140.5500),
    "川俣町": (37.6667, 140.6000), "大玉村": (37.5333, 140.4000),

    "鏡石町": (37.2500, 140.3500), "天栄村": (37.2333, 140.2667),

    "下郷町": (37.2667, 139.8667), "檜枝岐村": (37.0500, 139.2833),
    "只見町": (37.3500, 139.3167), "南会津町": (37.2000, 139.7667),

    "北塩原村": (37.6500, 139.9500), "西会津町": (37.5833, 139.6500),
    "磐梯町": (37.6000, 140.0333), "猪苗代町": (37.5500, 140.1000),

    "会津坂下町": (37.4667, 139.8333), "湯川村": (37.4667, 139.8833),
    "柳津町": (37.5333, 139.7167),

    "三島町": (37.4833, 139.6167), "金山町": (37.4500, 139.5333),
    "昭和村": (37.3500, 139.6167), "会津美里町": (37.4500, 139.8333),

    "西郷村": (37.1333, 140.1500), "泉崎村": (37.1500, 140.3000),
    "中島村": (37.1333, 140.3500), "矢吹町": (37.2000, 140.3333),

    "棚倉町": (37.0333, 140.3833), "矢祭町": (36.8667, 140.4167),
    "塙町": (36.9667, 140.4167), "鮫川村": (36.9500, 140.5167),

    "石川町": (37.1500, 140.4500), "玉川村": (37.2000, 140.4000),
    "平田村": (37.2000, 140.5667), "浅川町": (37.0833, 140.4167),
    "古殿町": (37.0833, 140.5667),

    "三春町": (37.4333, 140.4833), "小野町": (37.3000, 140.6333),

    "広野町": (37.2167, 140.9833), "楢葉町": (37.2833, 141.0000),
    "富岡町": (37.3333, 141.0000), "川内村": (37.3333, 140.8000),
    "大熊町": (37.4000, 141.0167), "双葉町": (37.4500, 141.0167),
    "浪江町": (37.4917, 141.0000), "葛尾村": (37.5000, 140.7667),

    "新地町": (37.8833, 140.9167), "飯舘村": (37.6667, 140.7333)
}

# ===== API =====
def safe_request(url):
    try:
        res = requests.get(url, timeout=5)
        if res.status_code != 200 or not res.text:
            return {}
        return res.json()
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
def pressure_color(p):
    return "red" if p < 990 else "orange" if p < 1000 else "green"

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
        t = current["main"]["temp"]

        st.markdown(f"<h1 style='color:{pressure_color(p)};'>📉 {p} hPa</h1>", unsafe_allow_html=True)
        st.write(f"🌡 気温: {t} ℃")
        st.write(f"🌬 風速: {w} m/s")

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
            <div style="min-width:160px;background:#eee;margin:5px;padding:10px;border-radius:10px;">
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
