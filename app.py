import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import feedparser
import requests
from bs4 import BeautifulSoup

st.set_page_config(layout="wide")
st.title("🏦 Autonomous Trading Engine")

# =========================
# SAFE HELPERS
# =========================

def safe_last(series):
    try: return series.iloc[-1]
    except: return 0

def safe_prev(series):
    try: return series.iloc[-2]
    except: return 0

def safe_vol(series):
    try: return series.pct_change().std()
    except: return 0

# =========================
# DATA
# =========================

@st.cache_data(ttl=60)
def get_data():
    return {
        "gold": yf.Ticker("GC=F").history(period="1d", interval="5m")["Close"],
        "silver": yf.Ticker("SI=F").history(period="1d", interval="5m")["Close"],
        "dxy": yf.Ticker("DX-Y.NYB").history(period="2d")["Close"],
        "yield": yf.Ticker("^TNX").history(period="2d")["Close"],
        "oil": yf.Ticker("CL=F").history(period="2d")["Close"],
        "usdinr": yf.Ticker("USDINR=X").history(period="2d")["Close"]
    }

data = get_data()

# =========================
# SENTIMENT
# =========================

def sentiment():
    try:
        feed = feedparser.parse("https://feeds.reuters.com/reuters/businessNews")
        headlines = [e.title.lower() for e in feed.entries[:5]]
    except:
        headlines = []

    score = 0
    for h in headlines:
        if "rate cut" in h or "stimulus" in h: score += 2
        if "war" in h or "attack" in h: score += 1
        if "recession" in h: score -= 1
        if "rate hike" in h: score -= 2

    return score

sent_score = sentiment()

# =========================
# ENTRY EXIT ZONES
# =========================

def entry_exit(series):

    if len(series) < 20:
        return 0,0,0,0

    support = series.rolling(20).min().iloc[-1]
    resistance = series.rolling(20).max().iloc[-1]

    ma = series.rolling(10).mean().iloc[-1]
    price = series.iloc[-1]

    vol = safe_vol(series)

    buy_zone = support * (1 + vol)
    sell_zone = resistance * (1 - vol)

    return price, buy_zone, sell_zone, ma

# =========================
# SIGNAL ENGINE
# =========================

def signal(price, buy, sell, ma):

    if price <= buy:
        return "🟢 BUY ZONE"
    elif price >= sell:
        return "🔴 SELL ZONE"
    elif price > ma:
        return "🟡 HOLD (UPTREND)"
    else:
        return "🟠 WAIT"

# =========================
# TOP TICKER
# =========================

st.markdown("## 📊 Live Market Ticker")

cols = st.columns(6)

assets = ["gold","silver","dxy","yield","oil","usdinr"]
labels = ["🥇 Gold","🥈 Silver","💵 DXY","📈 Yield","🛢️ Oil","🇮🇳 USDINR"]

signals = {}

for i, a in enumerate(assets):

    s = data[a]

    price, buy, sell, ma = entry_exit(s)

    sig = signal(price, buy, sell, ma)
    signals[a] = sig

    cols[i].metric(labels[i], f"{price:.2f}", sig)

st.divider()

# =========================
# DETAIL PANEL
# =========================

st.subheader("🎯 Entry / Exit Zones")

for a in assets:

    s = data[a]

    price, buy, sell, ma = entry_exit(s)

    st.write(f"### {a.upper()}")
    st.write(f"Price: {price:.2f}")
    st.write(f"🟢 Buy Zone: {buy:.2f}")
    st.write(f"🔴 Sell Zone: {sell:.2f}")
    st.write(f"📈 Trend (MA): {ma:.2f}")
    st.write(f"Signal: {signals[a]}")

# =========================
# CHART WITH ZONES
# =========================

st.subheader("📈 Gold Chart with Zones")

gold = data["gold"]

price, buy, sell, ma = entry_exit(gold)

fig = go.Figure()

fig.add_trace(go.Scatter(x=gold.index, y=gold, name="Price"))
fig.add_trace(go.Scatter(x=gold.index, y=[buy]*len(gold), name="Buy Zone"))
fig.add_trace(go.Scatter(x=gold.index, y=[sell]*len(gold), name="Sell Zone"))
fig.add_trace(go.Scatter(x=gold.index, y=[ma]*len(gold), name="MA"))

st.plotly_chart(fig, use_container_width=True)
