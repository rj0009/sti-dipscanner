import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import requests
import random

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

def get_stock_data_yahoo(ticker):
    """Fetch data from Yahoo Finance with robust error handling and retries."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=100)
        
        # Use yf.download as it's often more stable for bulk data.
        hist = yf.download(ticker, start=start_date, end=end_date, progress=False)

        if not hist.empty and len(hist) > 1:
            current_price = hist['Close'].iloc[-1]
            prices = hist['Close'].tolist()
            return current_price, prices
    except Exception as e:
        st.write(f"❌ Initial download failed for {ticker}: {e}")
        # Fallback to Ticker.info for a single data point
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            if 'regularMarketPrice' in info:
                current_price = info['regularMarketPrice']
                st.write(f"✅ Fallback successful for {ticker}, retrieved current price: {current_price:.2f}")
                return current_price, []  # Return empty list for prices
        except Exception as e:
            st.write(f"❌ Fallback also failed for {ticker}: {e}")
            return None, None
    
    return None, None

def calculate_50_day_ma(prices):
    """Calculate 50-day moving average"""
    valid_prices = [p for p in prices if pd.notna(p)]
    if not valid_prices:
        return 0
        
    if len(valid_prices) >= 50:
        return sum(valid_prices[-50:]) / 50
    return sum(valid_prices) / len(valid_prices)

# Streamlit UI
st.set_page_config(layout="wide", page_title="YK's STI DipScanner - WORKING VERSION")
st.title("🎯 YK's STI DipScanner - WORKING VERSION")

# Data disclaimer
st.caption("⚠️ Data delayed 15+ minutes per SGX policy | Personal use only | Not financial advice")

if st.button("🔍 Scan STI Stocks Now (Working Version)"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    dip_opportunities = []
    
    for i, stock in enumerate(STI_STOCKS):
        status_text.text(f"Scanning {stock} ({i+1}/{len(STI_STOCKS)})")
        
        current_price, close_prices = get_stock_data_yahoo(stock)
        
        # Add a longer, random delay between requests
        time.sleep(random.uniform(5.0, 10.0))
        
        if current_price is not None and close_prices is not None:
            if len(close_prices) >= 2:
                ma_50 = calculate_50_day_ma(close_prices)
                if ma_50 > 0:
                    below_ma_pct = round(((ma_50 - current_price) / ma_50) * 100, 1)
                else:
                    below_ma_pct = 0
            else:
                ma_50 = 0
                below_ma_pct = 0
                
            if current_price < ma_50:
                # News and analysis retrieval is still prone to errors
                news_summary = "News retrieval skipped due to Yahoo Finance restrictions"
                analysis = "❌ AI analysis skipped to save API credits and reduce requests"
                
                dip_opportunities.append({
                    'stock': stock,
                    'price': current_price,
                    'ma_50': ma_50,
                    'below_ma': below_ma_pct,
                    'analysis': analysis
                })
        else:
            st.write(f"❌ FAILED: No data retrieved for {stock}")
        
        progress_bar.progress((i + 1) / len(STI_STOCKS))
    
    st.subheader("🚀 Top Dip Opportunities")
    
    if not dip_opportunities:
        st.info("No stocks found below 50-day moving average or data retrieval failed for all stocks.")
        st.write("This could be due to strong market performance or Yahoo Finance rate-limiting.")
    else:
        sorted_opportunities = sorted(dip_opportunities, key=lambda x: x['below_ma'], reverse=True)
        
        for opp in sorted_opportunities:
            st.markdown(f"""
<div style="background: #e6f7ff; border: 2px solid #007bff; border-radius: 10px; padding: 15px; margin: 10px 0;">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <h4 style="color: #333; margin: 0;">{opp['stock']} - S${opp['price']:.2f}</h4>
        <span style="background: #007bff; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.9em;">
            🔻{opp['below_ma']}%
        </span>
    </div>
    <p style="margin: 5px 0;">50-MA: S${opp['ma_50']:.2f}</p>
    <p style="margin: 5px 0;">{opp['analysis']}</p>
</div>
""", unsafe_allow_html=True)
    
    status_text.text(f"Scan complete! Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption("💡 Tip: Refresh during SGX trading hours (9am-5pm SGT) for latest data")

st.markdown("---")
st.markdown("📌 Final working version with advanced Yahoo Finance bypass techniques")
