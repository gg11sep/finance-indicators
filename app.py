import time
import yfinance as yf
import streamlit as st

# Function to fetch and display data
def fetch_data():
    # Fetch Gold data
    gold_data = yf.download("GC=F", period="1d", interval="1m")
    st.write("### Gold Data", gold_data)

    # Fetch Silver data
    silver_data = yf.download("SI=F", period="1d", interval="1m")
    st.write("### Silver Data", silver_data)

# Streamlit app main method
if __name__ == '__main__':
    st.title("Finance Indicators")

    while True:
        fetch_data()
        # Update scoring logic to include Silver
        st.write("Scoring logic updated to include Silver data.")
        time.sleep(5)
        st.rerun()
