import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import requests

# Configuration
GROQ_KEY = os.getenv("GROQ_KEY", "your_groq_key_here")
# Verified STI constituents (30 stocks)
STI_STOCKS = [
    "D05.SI", "Z74.SI", "U11.SI", "O39.SI", "C38U.SI", 
    "ME8U.SI", "A17U.SI", "F34.SI", "C52.SI", "U96.SI",
    "D01.SI", "BN4.SI", "O2GA.SI", "BMK.SI", "C6L.SI",
    "F911.SI", "H78.SI", "K71U.SI", "N2IU.SI", "S58.SI",
    "S68.SI", "S63U.SI", "T39.SI", "Y92.SI", "C31.SI",
    "GK8.SI", "S59.SI", "Z78.SI", "NS8U.SI", "5FP.SI"
]

def get_stock_data(ticker):
    """Fetch data using yfinance with comprehensive debugging"""
    st.write(f"\n=== FETCHING DATA FOR {ticker} ===")
    
    try:
        # Create session with headers
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        })
        
        st.write(f"Attempting to create yf.Ticker object for {ticker}")
        stock = yf.Ticker(ticker, session=session)
        
        st.write(f"Attempting to get historical data for {ticker}")
        hist = stock.history(period="50d", interval="1d")
        
        st.write(f"Historical data shape: {hist.shape}")
        st.write(f"Is history empty? {hist.empty}")
        
        if hist.empty:
            st.write("Empty history returned")
            return None, None
            
        if len(hist) < 2:
            st.write(f"Insufficient data points: {len(hist)}")
            return None, None
            
        current_price = hist['Close'].iloc[-1]
        st.write(f"Current price: {current_price}")
        st.write(f"First 5 closing prices: {hist['Close'].head().tolist()}")
        
        return current_price, hist['Close'].tolist()
        
    except Exception as e:
        st.write(f"Exception occurred: {str(e)}")
        return None, None

def calculate_50_day_ma(prices):
    """Calculate 50-day moving average with debugging"""
    st.write(f"\n=== CALCULATING 50-DAY MA ===")
    st.write(f"Number of prices: {len(prices)}")
    
    valid_prices = [p for p in prices if pd.notna(p)]
    st.write(f"Valid prices count: {len(valid_prices)}")
    
    if not valid_prices:
        st.write("No valid prices found")
        return 0
        
    if len(valid_prices) >= 50:
        ma = sum(valid_prices[-50:]) / 50
        st.write(f"50-day MA: {ma}")
        return ma
        
    ma = sum(valid_prices) / len(valid_prices)
    st.write(f"MA with {len(valid_prices)} days: {ma}")
    return ma

# Streamlit UI - DEBUG MODE
st.set_page_config(layout="wide", page_title="YK's STI DipScanner - DEBUG")
st.title("🎯 YK's STI DipScanner - DEBUG MODE")

# Display environment info
st.subheader("Environment Information")
st.write(f"Streamlit version: {st.__version__}")
st.write(f"yfinance version: {yf.__version__}")
st.write(f"Pandas version: {pd.__version__}")

# Data disclaimer
st.caption("⚠️ Data delayed 15+ minutes per SGX policy | Personal use only | Not financial advice")

# Scan button
if st.button("🔍 Scan STI Stocks Now (DEBUG)"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    dip_opportunities = []
    failed_tickers = []
    
    for i, stock in enumerate(STI_STOCKS):
        status_text.text(f"Scanning {stock} ({i+1}/{len(STI_STOCKS)})")
        
        st.write(f"\n{'='*50}")
        st.write(f"PROCESSING: {stock}")
        st.write(f"{'='*50}")
        
        current_price, close_prices = get_stock_data(stock)
        
        if current_price and close_prices and len(close_prices) >= 2:
            st.write(f"✅ SUCCESS: Retrieved data for {stock}")
            
            ma_50 = calculate_50_day_ma(close_prices)
            below_ma_pct = round(((ma_50 - current_price) / ma_50) * 100, 1)
            st.write(f"📊 50-MA: {ma_50}, Current: {current_price}, Below MA: {below_ma_pct}%")
            
            # Check for dip (below 50-MA)
            if current_price < ma_50:
                st.write(f"🎯 DIP FOUND: {stock} is {below_ma_pct}% below 50-MA")
                dip_opportunities.append({
                    'stock': stock,
                    'price': current_price,
                    'ma_50': ma_50,
                    'below_ma': below_ma_pct,
                })
            else:
                st.write(f"📈 NO DIP: {stock} is above 50-MA")
        else:
            st.write(f"❌ FAILED: No data retrieved for {stock}")
            failed_tickers.append(stock)
        
        progress_bar.progress((i + 1) / len(STI_STOCKS))
        time.sleep(1.5)
    
    # Display results
    st.subheader("Results")
    
    st.write(f"✅ Successful: {len(dip_opportunities)} stocks")
    st.write(f"❌ Failed: {len(failed_tickers)} stocks")
    
    if failed_tickers:
        st.write("Failed tickers:", ", ".join(failed_tickers))
    
    if not dip_opportunities:
        st.info("No stocks found below 50-day moving average")
    else:
        st.success(f"Found {len(dip_opportunities)} stocks below 50-day MA!")
        for opp in dip_opportunities:
            st.write(f"{opp['stock']}: S${opp['price']:.2f} ({opp['below_ma']}% below)")
    
    status_text.text(f"Scan complete! Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
