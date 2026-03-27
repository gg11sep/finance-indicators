import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import feedparser
import time

st.set_page_config(layout="wide")
st.title("🏦 Autonomous Trading Dashboard")

# =========================
# AUTO REFRESH (FAST LOOP)
# =========================
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > 30:
    st.session_state.last_refresh = time.time()
    st.rerun()

# =========================
# SAFE DATA FETCH
# =========================
@st.cache_data(ttl=30)
def get_data():

    def fetch_safe(ticker, period="2d", interval=None):
        try:
            df = yf.Ticker(ticker).history(period=period, interval=interval)
            if df is None or df.empty:
                return pd.Series(dtype=float)
            return df["Close"]
        except:
            return pd.Series(dtype=float)

    return {
        "gold": fetch_safe("GC=F", "1d", "5m"),
        "silver": fetch_safe("SI=F", "1d", "5m"),
        "dxy": fetch_safe("DX-Y.NYB"),
        "yield": fetch_safe("^TNX"),
        "oil": fetch_safe("CL=F"),
        "usdinr": fetch_safe("USDINR=X")
    }

data = get_data()

# =========================
# SAFE VALUE HELPERS
# =========================
def get_last_valid(series):
    try:
        if series is None or len(series) == 0:
            return None
        return float(series.iloc[-1])
    except:
        return None

def get_prev_valid(series):
    try:
        if series is None or len(series) < 2:
            return None
        return float(series.iloc[-2])
    except:
        return None

# =========================
# ENTRY / EXIT LOGIC
# =========================
def entry_exit(series):

    if series is None or len(series) < 20:
        return None, None, None, None

    series = series.dropna()

    if len(series) < 20:
        return None, None, None, None

    support = series.rolling(20).min().iloc[-1]
    resistance = series.rolling(20).max().iloc[-1]
    ma = series.rolling(10).mean().iloc[-1]
    price = series.iloc[-1]

    vol = series.pct_change().std()

    buy_zone = support * (1 + vol)
    sell_zone = resistance * (1 - vol)

    return price, buy_zone, sell_zone, ma

# =========================
# SIGNAL ENGINE
# =========================
def generate_signal(price, prev):

    if price is None or prev is None:
        return "🟡 WAIT"

    change = (price - prev) / prev

    if change > 0.005:
        return "🚀 STRONG BUY"
    elif change > 0:
        return "🟢 BUY"
    elif change < -0.005:
        return "🔥 STRONG SELL"
    elif change < 0:
        return "🔴 SELL"
    else:
        return "🟡 WAIT"

# =========================
# SAFE NEWS (2 HOUR CACHE)
# =========================
@st.cache_data(ttl=7200)  # 2 hours
def get_news_safe():
    try:
        feed = feedparser.parse("https://feeds.reuters.com/reuters/businessNews")

        if not feed or not feed.entries:
            return []

        return [entry.title for entry in feed.entries[:8]]

    except:
        return []

# =========================
# TOP TICKER
# =========================
st.markdown("## 📊 Live Market Ticker")

cols = st.columns(6)

assets = [
    ("gold", "🥇 Gold", "$"),
    ("silver", "🥈 Silver", "$"),
    ("dxy", "💵 DXY", ""),
    ("yield", "📈 Yield", "%"),
    ("oil", "🛢️ Oil", "$"),
    ("usdinr", "🇮🇳 USDINR", "₹")
]

signals = {}

for i, (key, label, unit) in enumerate(assets):

    s = data[key]

    price = get_last_valid(s)
    prev = get_prev_valid(s)

    if price is None:
        cols[i].metric(label, "N/A", "⚠️ No Data")
        continue

    signal = generate_signal(price, prev)
    signals[key] = signal

    if unit == "%":
        display = f"{price:.2f}%"
    elif unit:
        display = f"{unit}{price:.2f}"
    else:
        display = f"{price:.2f}"

    cols[i].metric(label, display, signal)

st.divider()

# =========================
# ENTRY / EXIT PANEL
# =========================
st.subheader("🎯 Entry / Exit Zones")

for key, label, unit in assets:

    s = data[key]
    price, buy, sell, ma = entry_exit(s)

    st.write(f"### {label}")

    if price is None:
        st.write("⚠️ Not enough data")
        continue

    st.write(f"Price: {price:.2f}")
    st.write(f"🟢 Buy Zone: {buy:.2f}")
    st.write(f"🔴 Sell Zone: {sell:.2f}")
    st.write(f"📈 Trend (MA): {ma:.2f}")
    st.write(f"Signal: {signals.get(key,'-')}")

# =========================
# GOLD CHART WITH ZONES
# =========================
st.subheader("📈 Gold Chart with Zones")

gold = data["gold"]

price, buy, sell, ma = entry_exit(gold)

if price is not None:

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=gold.index, y=gold, name="Price"))
    fig.add_trace(go.Scatter(x=gold.index, y=[buy]*len(gold), name="Buy Zone"))
    fig.add_trace(go.Scatter(x=gold.index, y=[sell]*len(gold), name="Sell Zone"))
    fig.add_trace(go.Scatter(x=gold.index, y=[ma]*len(gold), name="MA"))

    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("⚠️ Not enough data for chart")

# =========================
# NEWS SECTION (SAFE + SLOW)
# =========================
st.subheader("📰 Market News (Updated every 2 hours)")

news = get_news_safe()

if news:
    for n in news:
        st.write("•", n)
else:
    st.write("⚠️ News unavailable")
