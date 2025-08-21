import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import random
import requests
from bs4 import BeautifulSoup

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

def get_yahoo_session():
    """Create a session with proper headers to avoid being blocked by Yahoo"""
    st.write("DEBUG: Creating Yahoo session with headers...")
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'DNT': '1',
        'Upgrade-Insecure-Requests': '1'
    })
    
    # Print headers for debugging
    st.write("DEBUG: Session headers:")
    for key, value in session.headers.items():
        st.write(f"  {key}: {value}")
    
    return session

def get_stock_data(ticker):
    """Fetch data using yfinance with enhanced debugging"""
    st.write(f"\nDEBUG: === STARTING SCAN FOR {ticker} ===")
    
    session = get_yahoo_session()
    
    # Verify connection to Yahoo Finance
    st.write("DEBUG: Testing connection to Yahoo Finance...")
    test_url = "https://finance.yahoo.com"
    try:
        test_response = session.get(test_url)
        st.write(f"DEBUG: Connection test to {test_url} - Status code: {test_response.status_code}")
        st.write(f"DEBUG: First 200 chars of response: {test_response.text[:200]}...")
        
        if "captcha" in test_response.text.lower() or "cloudflare" in test_response.text.lower():
            st.write("DEBUG: WARNING - Yahoo is showing CAPTCHA or Cloudflare protection!")
    except Exception as e:
        st.write(f"DEBUG: Connection test failed: {str(e)}")
        return None, None
    
    for attempt in range(3):
        st.write(f"\nDEBUG: Attempt {attempt+1} for {ticker}")
        
        try:
            # Check if ticker exists
            ticker_url = f"https://finance.yahoo.com/quote/{ticker}"
            st.write(f"DEBUG: Checking ticker existence at {ticker_url}")
            
            response = session.get(ticker_url)
            st.write(f"DEBUG: Ticker URL response status: {response.status_code}")
            
            if response.status_code != 200:
                st.write(f"DEBUG: Non-200 response: {response.text[:500]}")
            
            # Check for CAPTCHA or blocking
            if "captcha" in response.text.lower() or "cloudflare" in response.text.lower() or "sorry" in response.text.lower():
                st.write("DEBUG: WARNING - Yahoo is blocking this request with CAPTCHA/Cloudflare!")
                st.write(f"DEBUG: Response snippet: {response.text[:500]}")
                return None, None
            
            # Check if ticker exists
            if "Symbol Lookup" in response.text or "No result found" in response.text:
                st.write("DEBUG: Ticker not found on Yahoo Finance")
                st.write(f"DEBUG: Response snippet: {response.text[:500]}")
                return None, None
            
            # Try to get data
            st.write(f"DEBUG: Attempting to get historical data for {ticker}")
            stock = yf.Ticker(ticker, session=session)
            hist = stock.history(period="50d", interval="1d")
            
            st.write(f"DEBUG: Historical data shape: {hist.shape}")
            
            if hist.empty:
                st.write("DEBUG: Empty history returned")
                return None, None
                
            if len(hist) < 2:
                st.write(f"DEBUG: Not enough data points ({len(hist)} found)")
                return None, None
                
            current_price = hist['Close'].iloc[-1]
            st.write(f"DEBUG: Current price: {current_price}")
            st.write(f"DEBUG: First 5 closing prices: {hist['Close'].head().tolist()}")
            
            return current_price, hist['Close'].tolist()
            
        except Exception as e:
            st.write(f"DEBUG: Exception occurred: {str(e)}")
            st.write(f"DEBUG: Exception type: {type(e).__name__}")
            time.sleep(2 ** attempt)
    
    st.write("DEBUG: All attempts failed")
    return None, None

def calculate_50_day_ma(prices):
    """Calculate 50-day moving average"""
    st.write("\nDEBUG: === CALCULATING 50-DAY MA ===")
    st.write(f"DEBUG: Number of prices: {len(prices)}")
    
    valid_prices = [p for p in prices if pd.notna(p)]
    st.write(f"DEBUG: Number of valid prices: {len(valid_prices)}")
    
    if not valid_prices:
        st.write("DEBUG: No valid prices found")
        return 0
        
    if len(valid_prices) >= 50:
        ma = sum(valid_prices[-50:]) / 50
        st.write(f"DEBUG: Calculated MA (50 days): {ma}")
        return ma
        
    ma = sum(valid_prices) / len(valid_prices)
    st.write(f"DEBUG: Calculated MA ({len(valid_prices)} days): {ma}")
    return ma

def guru_analysis(stock, price, below_ma, news):
    """Get Groq-powered trading advice with debugging"""
    st.write("\nDEBUG: === RUNNING GROQ ANALYSIS ===")
    st.write(f"DEBUG: Stock: {stock}, Price: {price}, Below MA: {below_ma}%")
    st.write(f"DEBUG: News snippet: {news[:100]}...")
    
    import requests
    
    if not GROQ_KEY or GROQ_KEY == "your_groq_key_here" or "your_groq_key_here" in GROQ_KEY:
        st.write("DEBUG: GROQ_KEY is not properly set")
        return "❌ GROQ_KEY not set properly. Go to Settings → Secrets"
    
    st.write("DEBUG: GROQ_KEY is set (first 5 chars): " + GROQ_KEY[:5] +
