import streamlit as st
import yfinance as yf

st.title("📊 Gold-Silver Live Dashboard")

def get_data():
    dxy = yf.Ticker("DX-Y.NYB").history(period="2d")['Close']
    yield10 = yf.Ticker("^TNX").history(period="2d")['Close']
    gold = yf.Ticker("GC=F").history(period="2d")['Close']
    oil = yf.Ticker("CL=F").history(period="2d")['Close']

    return {
        "dxy": dxy.iloc[-1],
        "dxy_prev": dxy.iloc[-2],
        "yield": yield10.iloc[-1],
        "yield_prev": yield10.iloc[-2],
        "gold": gold.iloc[-1],
        "gold_prev": gold.iloc[-2],
        "oil": oil.iloc[-1],
        "oil_prev": oil.iloc[-2],
    }

def calculate_score(d):
    score = 0

    score += -1 if d["dxy"] > d["dxy_prev"] else 1
    score += -1 if d["yield"] > d["yield_prev"] else 1
    score += 1 if d["oil"] > d["oil_prev"] else -1
    score += -2 if d["gold"] < d["gold_prev"] else 2

    return score

data = get_data()
score = calculate_score(data)

# Signal
if score >= 3:
    signal = "🟢 STRONG BUY"
elif score >= 1:
    signal = "🟢 BUY"
elif score == 0:
    signal = "🟡 WAIT"
elif score >= -2:
    signal = "🟠 CAUTION"
else:
    signal = "🔴 STAY OUT"

# Display
st.metric("Gold", data["gold"])
st.metric("Dollar (DXY)", data["dxy"])
st.metric("Yield", data["yield"])
st.metric("Oil", data["oil"])

st.subheader(f"Score: {score}")
st.subheader(f"Signal: {signal}")
