import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# Configuration
GROQ_KEY = os.getenv("GROQ_KEY", "your_groq_key_here")
STI_STOCKS = [
    "D05.SI", "Z74.SI", "U11.SI", "O39.SI", "C38U.SI", 
    "ME8U.SI", "J69U.SI", "C09.SI", "A17U.SI", "F34.SI",
    "C52.SI", "U96.SI", "D01.SI", "BN4.SI", "O2GA.SI",
    "BMK.SI", "C6L.SI", "F911.SI", "H78.SI", "K71U.SI",
    "N2IU.SI", "S58.SI", "S68.SI", "S63U.SI", "T39.SI",
    "Y92.SI", "C31.SI", "GK8.SI", "S59.SI", "Z78.SI"
]

def get_stock_data(ticker):
    """Fetch data using yfinance with error handling"""
    try:
        stock = yf.Ticker(ticker)
        # Get 50-day history for MA calculation
        hist = stock.history(period="50d")
        if len(hist) < 2:
            return None, None
        # Get current price (last close)
        current_price = hist['Close'].iloc[-1]
        return current_price, hist['Close'].tolist()
    except Exception as e:
        st.warning(f"⚠️ {ticker}: {str(e)}")
        return None, None

def calculate_50_day_ma(prices):
    """Calculate 50-day moving average"""
    if len(prices) >= 50:
        return sum(prices) / 50
    return sum(prices) / len(prices) if prices else 0

def guru_analysis(stock, price, below_ma, news):
    """Get Groq-powered trading advice"""
    import requests
    
    if not GROQ_KEY or GROQ_KEY == "your_groq_key_here":
        return "❌ GROQ_KEY not set. Go to Settings → Secrets"
        
    payload = {
        "model": "mixtral-8x7b-32768",
        "messages": [{"role": "user", "content": f"""
        Role: SGX hedge fund manager with 15 years experience. 
        Analyze {stock} at S${price:.2f} ({below_ma}% below 50-MA). 
        Recent news: {news[:500]}... 
        Output ONLY:
        ✅ VERDICT: [BUY/HOLD/AVOID]
        🎯 1-WEEK TARGET: [PRICE]
        ⚠️ KEY RISK: [1 sentence]
        💡 ACTION: [Concise step]
        """}]
    }
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", 
                               json=payload, headers=headers, timeout=30)
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ AI analysis failed: {str(e)}"

# Streamlit UI
st.set_page_config(layout="wide", page_title="YK's STI DipScanner")
st.title("🎯 YK's STI DipScanner")

# Data disclaimer
st.caption("⚠️ Data delayed 15+ minutes per SGX policy | Personal use only | Not financial advice")

# Scan button
if st.button("🔍 Scan STI Stocks Now"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    dip_opportunities = []
    
    for i, stock in enumerate(STI_STOCKS):
        status_text.text(f"Scanning {stock} ({i+1}/{len(STI_STOCKS)})")
        
        current_price, close_prices = get_stock_data(stock)
        if current_price and close_prices and len(close_prices) >= 2:
            ma_50 = calculate_50_day_ma(close_prices)
            below_ma_pct = round(((ma_50 - current_price) / ma_50) * 100,
