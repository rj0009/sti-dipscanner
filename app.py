import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# Configuration
GROQ_KEY = os.getenv("GROQ_KEY")
STI_STOCKS = [
    "D05.SI", "Z74.SI", "U11.SI", "O39.SI", "C38U.SI", 
    "ME8U.SI", "J69U.SI", "C09.SI", "A17U.SI", "F34.SI",
    "C52.SI", "U96.SI", "D01.SI", "BN4.SI", "O2GA.SI",
    "BMK.SI", "C6L.SI", "F911.SI", "H78.SI", "K71U.SI",
    "N2IU.SI", "S58.SI", "S68.SI", "S63U.SI", "T39.SI",
    "Y92.SI", "C31.SI", "GK8.SI", "S59.SI", "Z78.SI"
]

def get_stock_data(ticker):
    """Fetch data using yfinance (free, no limits)"""
    try:
        stock = yf.Ticker(ticker)
        intraday = stock.history(period="1d", interval="5m")
        hist = stock.history(period="50d")
        return intraday, hist['Close'].tolist()
    except Exception as e:
        st.error(f"Error fetching {ticker}: {str(e)}")
        return None, None

def calculate_50_day_ma(prices):
    """Calculate 50-day moving average"""
    return sum(prices) / len(prices) if prices else 0

def get_news_summary(ticker):
    """Extract news headlines from Yahoo Finance"""
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        return " | ".join([item['title'] for item in news[:3]]) if news else "No recent news"
    except:
        return "News unavailable"

def guru_analysis(stock, price, below_ma, news):
    """Get Groq-powered trading advice"""
    import requests
    
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
                               json=payload, headers=headers)
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ Analysis failed: {str(e)}"

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
        
        intraday, close_prices = get_stock_data(stock)
        if close_prices and len(close_prices) >= 2:
            current_price = close_prices[-1]
            ma_50 = calculate_50_day_ma(close_prices)
            below_ma_pct = round(((ma_50 - current_price) / ma_50) * 100, 1)
            
            if current_price < ma_50:
                news = get_news_summary(stock)
                analysis = guru_analysis(stock, current_price, below_ma_pct, news)
                
                dip_opportunities.append({
                    'stock': stock,
                    'price': current_price,
                    'below_ma': below_ma_pct,
                    'analysis': analysis,
                    'news': news
                })
        
        progress_bar.progress((i + 1) / len(STI_STOCKS))
        time.sleep(1)
    
    # Display results
    st.subheader("🚀 Top Dip Opportunities")
    
    if not dip_opportunities:
        st.info("No stocks found below 50-day moving average. Try again later!")
    else:
        for opp in sorted(dip_opportunities, key=lambda x: x['below_ma'], reverse=True):
            lines = opp['analysis'].split('\n')
            verdict = next((l for l in lines if l.startswith("✅ VERDICT")), "✅ VERDICT: HOLD")
            target = next((l for l in lines if l.startswith("🎯 1-WEEK TARGET")), "🎯 1-WEEK TARGET: N/A")
            risk = next((l for l in lines if l.startswith("⚠️ KEY RISK")), "⚠️ KEY RISK: Market volatility")
            action = next((l for l in lines if l.startswith("💡 ACTION")), "💡 ACTION: Monitor")
            
            color = "green" if "BUY" in verdict else "orange" if "HOLD" in verdict else "red"
            bg_color = "#f0fff0" if "BUY" in verdict else "#fffaf0" if "HOLD" in verdict else "#fff0f0"
            
            st.markdown(f"""
            <div style="background: {bg_color}; border: 2px solid {color}; border-radius: 10px; padding: 15px; margin: 10px 0;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h4 style="color: #333; margin: 0;">{opp['stock']} - S${opp['price']:.2f}</h4>
                    <span style="background: {color}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.9em;">
                        🔻{opp['below_ma']}%
                    </span>
                </div>
                <p style="color: {color}; font-weight: bold; margin: 8px 0;">{verdict}</p>
                <p style="margin: 5px 0;">{target}</p>
                <p style="margin: 5px 0;">⚠️ {risk}</p>
                <p style="margin: 5px 0;">💡 {action}</p>
                <details style="margin: 10px 0; font-size: 0.9em;">
                    <summary>📰 Recent News</summary>
                    {opp['news']}
                </details>
            </div>
            """, unsafe_allow_html=True)
    
    status_text.text(f"Scan complete! Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption("💡 Tip: Refresh during SGX trading hours (9am-5pm SGT) for latest data")

# Footer
st.markdown("---")
st.markdown("📌 **How it works**: Scans all 30 STI stocks for 50-day MA breaches → Uses Groq AI for trading advice → Presents Netflix-style recommendations")
