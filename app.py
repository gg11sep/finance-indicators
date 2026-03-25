import streamlit as st
import yfinance as yf
import time
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("📊 Gold-Silver Live Dashboard")

if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

@st.cache_data(ttl=60)
def get_data():
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            dxy = yf.Ticker("DX-Y.NYB").history(period="2d")['Close']
            yield10 = yf.Ticker("^TNX").history(period="2d")['Close']
            gold = yf.Ticker("GC=F").history(period="1d", interval="5m")['Close']
            silver = yf.Ticker("SI=F").history(period="1d", interval="5m")['Close']
            oil = yf.Ticker("CL=F").history(period="2d")['Close']
            usd_inr = yf.Ticker("USDINR=X").history(period="1d")['Close']

            return {
                "dxy": dxy.iloc[-1],
                "dxy_prev": dxy.iloc[-2],
                "yield": yield10.iloc[-1],
                "yield_prev": yield10.iloc[-2],
                "gold": gold,
                "gold_current": gold.iloc[-1],
                "gold_prev": gold.iloc[-2],
                "silver": silver,
                "silver_current": silver.iloc[-1],
                "silver_prev": silver.iloc[-2],
                "oil": oil.iloc[-1],
                "oil_prev": oil.iloc[-2],
                "usd_inr": usd_inr.iloc[-1],
            }
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                st.error(f"⚠️ Unable to fetch data: {str(e)}")
                st.info("Yahoo Finance may be rate limiting. Please refresh in a moment.")
                return None

def get_signal(score):
    if score >= 2:           # Changed from 3
        return "🟢 STRONG BUY"
    elif score >= 1:
        return "🟢 BUY"
    elif score >= 0:         # Changed from -1
        return "🟡 WAIT"
    elif score >= -1:        # Changed from -2
        return "🟠 CAUTION"
    else:
        return "🔴 STAY OUT"

def calculate_gold_score(gold_val, gold_prev, dxy_val, dxy_prev, yield_val, yield_prev, oil_val, oil_prev):
    score = 0
    score += -1 if dxy_val > dxy_prev else 1
    score += -1 if yield_val > yield_prev else 1
    score += 1 if oil_val > oil_prev else -1
    score += -2 if gold_val < gold_prev else 2
    return score

def calculate_silver_score(silver_val, silver_prev, dxy_val, dxy_prev, yield_val, yield_prev, oil_val, oil_prev):
    score = 0
    score += -1 if dxy_val > dxy_prev else 1
    score += -1 if yield_val > yield_prev else 1
    score += 1 if oil_val > oil_prev else -1
    score += -2 if silver_val < silver_prev else 2
    return score

def create_price_chart(data, title, hex_color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data.values,
        mode='lines',
        line=dict(color=hex_color, width=2),
        fill='tozeroy',
        fillcolor=hex_color
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title="Price (USD)",
        hovermode='x unified',
        height=400,
        margin=dict(l=50, r=50, t=50, b=50),
        template='plotly_dark'
    )
    return fig

if time.time() - st.session_state.last_refresh > 5:
    st.session_state.last_refresh = time.time()
    st.rerun()

data = get_data()

if data:
    # Calculate SEPARATE scores for Gold and Silver
    gold_score = calculate_gold_score(
        data["gold_current"], data["gold_prev"],
        data["dxy"], data["dxy_prev"],
        data["yield"], data["yield_prev"],
        data["oil"], data["oil_prev"]
    )
    
    silver_score = calculate_silver_score(
        data["silver_current"], data["silver_prev"],
        data["dxy"], data["dxy_prev"],
        data["yield"], data["yield_prev"],
        data["oil"], data["oil_prev"]
    )
    
    gold_signal = get_signal(gold_score)
    silver_signal = get_signal(silver_score)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("💵 Dollar (DXY)", f"{data['dxy']:.2f}", 
                  delta=f"{data['dxy']-data['dxy_prev']:.4f}")
    with col2:
        st.metric("📈 Yield (10Y)", f"{data['yield']:.2f}%", 
                  delta=f"{data['yield']-data['yield_prev']:.4f}")
    with col3:
        st.metric("🛢️ Oil", f"${data['oil']:.2f}", 
                  delta=f"{data['oil']-data['oil_prev']:.2f}")
    with col4:
        st.metric("🇮🇳 USD to INR", f"₹{data['usd_inr']:.2f}")
    with col5:
        avg_score = (gold_score + silver_score) / 2
        st.metric("📊 Avg Score", f"{avg_score:.1f}")

    st.divider()

    col_gold, col_silver = st.columns(2)
    
    with col_gold:
        st.markdown("### 🥇 Gold")
        st.metric("Signal", gold_signal, delta=f"Score: {gold_score}")
        gold_usd = data['gold_current']
        gold_inr = gold_usd * data['usd_inr']
        st.metric("USD Price", f"${gold_usd:.2f}", 
                  delta=f"${data['gold_current']-data['gold_prev']:.2f}")
        st.metric("INR Price", f"₹{gold_inr:.2f}", 
                  delta=f"₹{(data['gold_current']-data['gold_prev'])*data['usd_inr']:.2f}")
        gold_chart = create_price_chart(data["gold"], "Gold Price (24H)", "#FFC107")
        st.plotly_chart(gold_chart, use_container_width=True)
    
    with col_silver:
        st.markdown("### 🥈 Silver")
        st.metric("Signal", silver_signal, delta=f"Score: {silver_score}")
        silver_usd = data['silver_current']
        silver_inr = silver_usd * data['usd_inr']
        st.metric("USD Price", f"${silver_usd:.2f}", 
                  delta=f"${data['silver_current']-data['silver_prev']:.2f}")
        st.metric("INR Price", f"₹{silver_inr:.2f}", 
                  delta=f"₹{(data['silver_current']-data['silver_prev'])*data['usd_inr']:.2f}")
        silver_chart = create_price_chart(data["silver"], "Silver Price (24H)", "#C0C0C0")
        st.plotly_chart(silver_chart, use_container_width=True)

    st.divider()
    st.markdown("## 📊 Signal Summary")
    col_summary1, col_summary2 = st.columns(2)
    with col_summary1:
        st.markdown(f"### Gold: {gold_signal}")
        st.markdown(f"**Score:** {gold_score}")
    with col_summary2:
        st.markdown(f"### Silver: {silver_signal}")
        st.markdown(f"**Score:** {silver_score}")
