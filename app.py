import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import feedparser
import time

st.set_page_config(layout="wide")
st.title("🏦 Autonomous Trading Dashboard")

# =========================
# AUTO REFRESH
# =========================
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > 30:
    st.session_state.last_refresh = time.time()
    st.rerun()

# =========================
# DATA FETCH (ROBUST)
# =========================
@st.cache_data(ttl=30)
def get_data():

    def fetch_multi(tickers, period="2d", interval=None):
        for t in tickers:
            try:
                df = yf.Ticker(t).history(period=period, interval=interval)
                if df is not None and not df.empty:
                    return df["Close"]
            except:
                continue
        return pd.Series(dtype=float)

    return {
        "gold": fetch_multi(["GC=F"], "1d", "5m"),
        "silver": fetch_multi(["SI=F"], "1d", "5m"),
        "dxy": fetch_multi(["DX-Y.NYB", "DX=F"]),
        "yield": fetch_multi(["^TNX", "^IRX"]),
        "oil": fetch_multi(["CL=F", "BZ=F"]),
        "usdinr": fetch_multi(["USDINR=X"])
    }

data = get_data()

# =========================
# SAFE HELPERS
# =========================
def last(series):
    try:
        return float(series.iloc[-1])
    except:
        return None

def prev(series):
    try:
        return float(series.iloc[-2])
    except:
        return None

# =========================
# SIGNAL ENGINE
# =========================
def signal(p, pr):
    if p is None or pr is None:
        return "🟡 WAIT"

    change = (p - pr) / pr

    if change > 0.005:
        return "🚀 STRONG BUY"
    elif change > 0:
        return "🟢 BUY"
    elif change < -0.005:
        return "🔥 STRONG SELL"
    elif change < 0:
        return "🔴 SELL"
    return "🟡 WAIT"

# =========================
# ENTRY / EXIT
# =========================
def entry_exit(series):

    if series is None or len(series) < 20:
        return None, None, None, None

    s = series.dropna()

    if len(s) < 20:
        return None, None, None, None

    support = s.rolling(20).min().iloc[-1]
    resistance = s.rolling(20).max().iloc[-1]
    ma = s.rolling(10).mean().iloc[-1]
    price = s.iloc[-1]

    vol = s.pct_change().std()

    buy = support * (1 + vol)
    sell = resistance * (1 - vol)

    return price, buy, sell, ma

# =========================
# OUTLOOK
# =========================
def outlook(series):

    if series is None or len(series) < 50:
        return "⚠️ No Data", "⚠️ No Data"

    s = series.dropna()
    price = s.iloc[-1]

    ma50 = s.rolling(50).mean().iloc[-1]
    ma200 = s.rolling(200).mean().iloc[-1] if len(s) >= 200 else ma50

    mid = "🟢 Bullish (1–4W)" if price > ma50 else "🔴 Bearish (1–4W)"
    long = "🚀 Bullish (3–12M)" if price > ma200 else "⚠️ Weak (3–12M)"

    return mid, long

# =========================
# NEWS (SAFE)
# =========================
@st.cache_data(ttl=7200)
def get_news():
    try:
        feed = feedparser.parse("https://feeds.reuters.com/reuters/businessNews")
        return [e.title for e in feed.entries[:8]]
    except:
        return []

# =========================
# TICKER
# =========================
st.markdown("## 📊 Live Market Ticker")

cols = st.columns(6)

assets = [
    ("gold","🥇 Gold","$"),
    ("silver","🥈 Silver","$"),
    ("dxy","💵 DXY",""),
    ("yield","📈 Yield","%"),
    ("oil","🛢️ Oil","$"),
    ("usdinr","🇮🇳 USDINR","₹")
]

signals = {}

for i,(k,l,u) in enumerate(assets):

    p = last(data[k])
    pr = prev(data[k])

    if p is None:
        cols[i].metric(l,"N/A","⚠️ No Data")
        continue

    sig = signal(p,pr)
    signals[k] = sig

    val = f"{u}{p:.2f}" if u and u!="%" else f"{p:.2f}%" if u=="%" else f"{p:.2f}"
    cols[i].metric(l,val,sig)

st.divider()

# =========================
# OUTLOOK PANEL
# =========================
st.subheader("📊 Medium & Long Term Outlook")

for k,l,_ in assets:
    mid,long = outlook(data[k])
    st.write(f"### {l}")
    st.write(f"Medium: {mid}")
    st.write(f"Long: {long}")

# =========================
# ENTRY EXIT
# =========================
st.subheader("🎯 Entry / Exit Zones")

for k,l,_ in assets:

    p,b,s,m = entry_exit(data[k])

    st.write(f"### {l}")

    if p is None:
        st.write("⚠️ Not enough data")
        continue

    st.write(f"Price: {p:.2f}")
    st.write(f"🟢 Buy Zone: {b:.2f}")
    st.write(f"🔴 Sell Zone: {s:.2f}")
    st.write(f"📈 MA: {m:.2f}")
    st.write(f"Signal: {signals.get(k,'-')}")

# =========================
# CHART FUNCTION
# =========================
def plot_chart(series, title):

    p,b,s,m = entry_exit(series)

    if p is None:
        st.warning("⚠️ Not enough data")
        return

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=series.index,y=series,name="Price"))
    fig.add_trace(go.Scatter(x=series.index,y=[b]*len(series),name="Buy Zone"))
    fig.add_trace(go.Scatter(x=series.index,y=[s]*len(series),name="Sell Zone"))
    fig.add_trace(go.Scatter(x=series.index,y=[m]*len(series),name="MA"))

    fig.update_layout(title=title)

    st.plotly_chart(fig,use_container_width=True)

# =========================
# GOLD CHART
# =========================
st.subheader("📈 Gold Chart")
plot_chart(data["gold"],"Gold")

# =========================
# SILVER CHART
# =========================
st.subheader("📈 Silver Chart")
plot_chart(data["silver"],"Silver")

# =========================
# NEWS
# =========================
st.subheader("📰 Market News (2h refresh)")

news = get_news()

if news:
    for n in news:
        st.write("•",n)
else:
    st.write("⚠️ News unavailable")

# =========================
# MACRO INSIGHT
# =========================
st.subheader("🧠 Macro Insight")

g_mid,g_long = outlook(data["gold"])
d_mid,d_long = outlook(data["dxy"])

if "Bullish" in g_long and "Bearish" in d_mid:
    st.success("🔥 Strong macro tailwind for Gold/Silver")

elif "Bearish" in g_mid:
    st.warning("⚠️ Short-term pressure on metals")

else:
    st.info("🟡 Mixed signals")
