import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🏦 Institutional Macro Trading Engine")

# ---------------- DATA ---------------- #
@st.cache_data(ttl=60)
def get_live_data():
    return {
        "gold": yf.Ticker("GC=F").history(period="1d", interval="5m")["Close"],
        "silver": yf.Ticker("SI=F").history(period="1d", interval="5m")["Close"],
        "dxy": yf.Ticker("DX-Y.NYB").history(period="2d")["Close"],
        "yield": yf.Ticker("^TNX").history(period="2d")["Close"],
        "oil": yf.Ticker("CL=F").history(period="5d")["Close"],
        "vix": yf.Ticker("^VIX").history(period="2d")["Close"],
    }

# ---------------- REGIME ---------------- #
def detect_regime(d):
    if d["gold"].iloc[-1] > d["gold"].iloc[-2] and d["oil"].iloc[-1] > d["oil"].iloc[-2]:
        return "🔥 Stagflation"
    elif d["dxy"].iloc[-1] > d["dxy"].iloc[-2] and d["yield"].iloc[-1] > d["yield"].iloc[-2]:
        return "🔴 Liquidity Crisis"
    return "🟡 Transition"

# ---------------- ALLOCATION ---------------- #
def regime_allocation(regime):
    if regime == "🔥 Stagflation":
        return {"gold":50,"silver":40,"cash":10}
    elif regime == "🔴 Liquidity Crisis":
        return {"gold":20,"silver":10,"cash":70}
    return {"gold":40,"silver":30,"cash":30}

# ---------------- RISK MODEL ---------------- #
def volatility(series):
    return series.pct_change().std()

def adjust_alloc(alloc, g_vol, s_vol):
    if g_vol > 0.01: alloc["gold"] *= 0.7
    if s_vol > 0.015: alloc["silver"] *= 0.6
    total = sum(alloc.values())
    return {k: round(v/total*100,1) for k,v in alloc.items()}

def kelly(conf):
    return 1.2 if conf>80 else 1.0 if conf>60 else 0.7

# ---------------- PORTFOLIO ---------------- #
class Portfolio:
    def _init_(self):
        self.capital=100000

    def allocate(self, alloc, g_price, s_price):
        self.gold = self.capital*alloc["gold"]/100/g_price
        self.silver = self.capital*alloc["silver"]/100/s_price
        self.cash = self.capital*alloc["cash"]/100

    def value(self, g_price, s_price):
        return self.gold*g_price + self.silver*s_price + self.cash

# ---------------- BACKTEST ---------------- #
@st.cache_data
def get_hist():
    return pd.DataFrame({
        "gold": yf.Ticker("GC=F").history(period="2y")["Close"],
        "silver": yf.Ticker("SI=F").history(period="2y")["Close"],
        "dxy": yf.Ticker("DX-Y.NYB").history(period="2y")["Close"],
        "yield": yf.Ticker("^TNX").history(period="2y")["Close"],
        "oil": yf.Ticker("CL=F").history(period="2y")["Close"],
        "vix": yf.Ticker("^VIX").history(period="2y")["Close"],
    }).dropna()

def backtest(df):
    cap=100000
    vals=[]
    for i in range(5,len(df)):
        row, prev = df.iloc[i], df.iloc[i-1]
        regime = "🔥 Stagflation" if row["gold"]>prev["gold"] and row["oil"]>prev["oil"] else "🟡"
        alloc = regime_allocation(regime)

        cap = cap*(1 + (row["gold"]/prev["gold"]-1)*alloc["gold"]/100 +
                         (row["silver"]/prev["silver"]-1)*alloc["silver"]/100)

        vals.append(cap)
    return pd.Series(vals, index=df.index[-len(vals):])

# ---------------- METRICS ---------------- #
def metrics(s):
    r=s.pct_change().dropna()
    ret=(s.iloc[-1]/s.iloc[0]-1)*100
    sharpe=(r.mean()/r.std())*np.sqrt(252)
    dd=((s-s.cummax())/s.cummax()).min()*100
    return ret, sharpe, dd

# ---------------- MONTE CARLO ---------------- #
def monte(s, n=100):
    r=s.pct_change().dropna().values
    return [100000*np.cumprod(1+np.random.choice(r,len(r)))[-1] for _ in range(n)]

# ---------------- BENCHMARK ---------------- #
def benchmark(df):
    gold=100000*(df["gold"]/df["gold"].iloc[0])
    silver=100000*(df["silver"]/df["silver"].iloc[0])
    return gold, silver

# ---------------- ROBUSTNESS ---------------- #
def robustness(s):
    r=s.pct_change().dropna()
    return round((r.mean()/r.std())*0.6 + (r>0).mean()*0.4,2)

# ---------------- MAIN ---------------- #
live = get_live_data()
regime = detect_regime(live)

g_price = live["gold"].iloc[-1]
s_price = live["silver"].iloc[-1]

g_vol = volatility(live["gold"])
s_vol = volatility(live["silver"])

alloc = regime_allocation(regime)
alloc = adjust_alloc(alloc, g_vol, s_vol)

pf = Portfolio()
pf.allocate(alloc, g_price, s_price)
value = pf.value(g_price, s_price)

# ---------------- UI ---------------- #
st.metric("Regime", regime)
st.metric("Portfolio Value", f"₹{value:,.0f}")

st.write("Allocation:", alloc)

# ---------------- BACKTEST ---------------- #
st.subheader("📈 Backtesting")

df = get_hist()
bt = backtest(df)

ret, sharpe, dd = metrics(bt)

col1,col2,col3 = st.columns(3)
col1.metric("Return", f"{ret:.2f}%")
col2.metric("Sharpe", f"{sharpe:.2f}")
col3.metric("Drawdown", f"{dd:.2f}%")

# ---------------- MONTE ---------------- #
mc = monte(bt)
st.write(f"Monte Carlo Avg: {sum(mc)/len(mc):,.0f}")

# ---------------- ROBUSTNESS ---------------- #
st.metric("Robustness", robustness(bt))

# ---------------- CHART ---------------- #
gold_bh, silver_bh = benchmark(df)

fig = go.Figure()
fig.add_trace(go.Scatter(x=bt.index, y=bt, name="Strategy"))
fig.add_trace(go.Scatter(x=gold_bh.index, y=gold_bh, name="Gold"))
fig.add_trace(go.Scatter(x=silver_bh.index, y=silver_bh, name="Silver"))

st.plotly_chart(fig, use_container_width=True)
