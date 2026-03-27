import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import feedparser
import requests
from bs4 import BeautifulSoup

st.set_page_config(layout="wide")
st.title("🏦 Autonomous Macro Trading Engine")

# =========================
# ===== SENTIMENT ENGINE ==
# =========================

POSITIVE = ["stimulus","rate cut","liquidity","qe","bailout","safe haven","dovish"]
NEGATIVE = ["rate hike","strong dollar","rising yields","tightening","hawkish","selloff"]
GEO = ["war","attack","iran","russia","conflict","missile"]
RISK = ["recession","crisis","slowdown","defaults"]

def score_text(text):
    score = 0
    for w in POSITIVE:
        if w in text: score += 2
    for w in NEGATIVE:
        if w in text: score -= 2
    for w in GEO:
        if w in text: score += 1
    for w in RISK:
        if w in text: score -= 1
    return score

def get_news():
    urls = [
        "https://feeds.reuters.com/reuters/businessNews",
        "https://feeds.reuters.com/reuters/worldNews"
    ]
    headlines = []
    for u in urls:
        try:
            feed = feedparser.parse(u)
            for e in feed.entries[:5]:
                headlines.append(e.title.lower())
        except:
            pass
    return headlines

def get_twitter():
    try:
        url = "https://nitter.net/search?f=tweets&q=gold%20silver%20oil"
        r = requests.get(url, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")
        return [t.get_text().lower() for t in soup.select(".tweet-content")[:10]]
    except:
        return []

def sentiment_engine():
    news = get_news()
    tweets = get_twitter()

    all_text = news + tweets

    total = sum(score_text(t) for t in all_text)

    if total >= 10:
        signal, conf = "🚀 Strong Bullish", 90
    elif total >= 5:
        signal, conf = "🟢 Bullish", 70
    elif total >= 0:
        signal, conf = "🟡 Neutral", 50
    elif total >= -5:
        signal, conf = "🟠 Bearish", 30
    else:
        signal, conf = "🔴 Strong Bearish", 10

    return signal, conf, news, tweets

def sentiment_score(signal):
    if "Strong Bullish" in signal: return 3
    if "Bullish" in signal: return 2
    if "Bearish" in signal: return -2
    if "Strong Bearish" in signal: return -3
    return 0

# =========================
# ===== DATA ==============
# =========================

@st.cache_data(ttl=60)
def get_live():
    return {
        "gold": yf.Ticker("GC=F").history(period="1d", interval="5m")["Close"],
        "silver": yf.Ticker("SI=F").history(period="1d", interval="5m")["Close"],
        "dxy": yf.Ticker("DX-Y.NYB").history(period="2d")["Close"],
        "yield": yf.Ticker("^TNX").history(period="2d")["Close"],
        "oil": yf.Ticker("CL=F").history(period="2d")["Close"],
        "vix": yf.Ticker("^VIX").history(period="2d")["Close"],
    }

# =========================
# ===== REGIME ============
# =========================

def regime(d):
    if d["gold"].iloc[-1] > d["gold"].iloc[-2] and d["oil"].iloc[-1] > d["oil"].iloc[-2]:
        return "🔥 Stagflation"
    elif d["dxy"].iloc[-1] > d["dxy"].iloc[-2]:
        return "🔴 Liquidity Crisis"
    return "🟡 Transition"

def allocation(r):
    if "Stagflation" in r:
        return {"gold":50,"silver":40,"cash":10}
    elif "Liquidity" in r:
        return {"gold":20,"silver":10,"cash":70}
    return {"gold":40,"silver":30,"cash":30}

# =========================
# ===== RISK MODEL ========
# =========================

def vol(series):
    return series.pct_change().std()

def adjust_alloc(a, gv, sv):
    if gv > 0.01: a["gold"] *= 0.7
    if sv > 0.015: a["silver"] *= 0.6
    tot = sum(a.values())
    return {k: round(v/tot*100,1) for k,v in a.items()}

# =========================
# ===== PORTFOLIO =========
# =========================

class Portfolio:
    def _init_(self):
        self.cap = 100000

    def alloc(self, a, gp, sp):
        self.g = self.cap * a["gold"]/100 / gp
        self.s = self.cap * a["silver"]/100 / sp
        self.c = self.cap * a["cash"]/100

    def val(self, gp, sp):
        return self.g*gp + self.s*sp + self.c

# =========================
# ===== BACKTEST ==========
# =========================

@st.cache_data
def hist():
    return pd.DataFrame({
        "gold": yf.Ticker("GC=F").history(period="2y")["Close"],
        "silver": yf.Ticker("SI=F").history(period="2y")["Close"],
        "dxy": yf.Ticker("DX-Y.NYB").history(period="2y")["Close"],
        "yield": yf.Ticker("^TNX").history(period="2y")["Close"],
        "oil": yf.Ticker("CL=F").history(period="2y")["Close"],
    }).dropna()

def backtest(df):
    cap = 100000
    vals = []

    for i in range(5,len(df)):
        row, prev = df.iloc[i], df.iloc[i-1]

        r = "🔥 Stagflation" if row["gold"]>prev["gold"] else "🟡"
        a = allocation(r)

        cap *= (1 +
            (row["gold"]/prev["gold"]-1)*a["gold"]/100 +
            (row["silver"]/prev["silver"]-1)*a["silver"]/100)

        vals.append(cap)

    return pd.Series(vals, index=df.index[-len(vals):])

# =========================
# ===== METRICS ===========
# =========================

def metrics(s):
    r = s.pct_change().dropna()
    ret = (s.iloc[-1]/s.iloc[0]-1)*100
    sharpe = (r.mean()/r.std())*np.sqrt(252)
    dd = ((s-s.cummax())/s.cummax()).min()*100
    return ret, sharpe, dd

def monte(s):
    r = s.pct_change().dropna().values
    sims = [100000*np.cumprod(1+np.random.choice(r,len(r)))[-1] for _ in range(100)]
    return sims

def robustness(s):
    r = s.pct_change().dropna()
    return round((r.mean()/r.std())*0.6 + (r>0).mean()*0.4,2)

# =========================
# ===== MAIN ==============
# =========================

data = get_live()
reg = regime(data)

gp = data["gold"].iloc[-1]
sp = data["silver"].iloc[-1]

gv = vol(data["gold"])
sv = vol(data["silver"])

alloc = allocation(reg)
alloc = adjust_alloc(alloc, gv, sv)

pf = Portfolio()
pf.alloc(alloc, gp, sp)
val = pf.val(gp, sp)

# SENTIMENT
signal, conf, news, tweets = sentiment_engine()
sent_score = sentiment_score(signal)

# =========================
# ===== UI ================
# =========================

st.metric("Regime", reg)
st.metric("Portfolio Value", f"${val:,.0f}")
st.write("Allocation:", alloc)

st.subheader("🧠 Sentiment Engine")
st.metric("Signal", signal)
st.metric("Confidence", f"{conf}%")

st.write("### News")
for n in news:
    st.write("•", n)

st.write("### Twitter")
for t in tweets:
    st.write("•", t[:100])

# =========================
# ===== BACKTEST ==========
# =========================

st.subheader("📈 Backtest")

df = hist()
bt = backtest(df)

ret, sharpe, dd = metrics(bt)

col1,col2,col3 = st.columns(3)
col1.metric("Return", f"{ret:.2f}%")
col2.metric("Sharpe", f"{sharpe:.2f}")
col3.metric("Drawdown", f"{dd:.2f}%")

st.metric("Robustness", robustness(bt))

mc = monte(bt)
st.write(f"Monte Carlo Avg: {sum(mc)/len(mc):,.0f}")

# Chart
fig = go.Figure()
fig.add_trace(go.Scatter(x=bt.index, y=bt, name="Strategy"))
st.plotly_chart(fig, use_container_width=True)
