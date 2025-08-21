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
            below_ma_pct = round(((ma_50 - current_price) / ma_50) * 100, 1)
            
            # Check for dip (below 50-MA)
            if current_price < ma_50 * 1.02:
                # Get news summary
                try:
                    stock_obj = yf.Ticker(stock)
                    news = stock_obj.news
                    news_summary = " | ".join([item['title'] for item in news[:3]]) if news else "No recent news"
                except:
                    news_summary = "News unavailable"
                
                # Get guru analysis
                analysis = guru_analysis(stock, current_price, below_ma_pct, news_summary)
                
                dip_opportunities.append({
                    'stock': stock,
                    'price': current_price,
                    'ma_50': ma_50,
                    'below_ma': below_ma_pct,
                    'analysis': analysis
                })
        
        progress_bar.progress((i + 1) / len(STI_STOCKS))
        time.sleep(1.5)  # Be gentle with Yahoo's servers
    
    # Display results
    st.subheader("🚀 Top Dip Opportunities")
    
    if not dip_opportunities:
        st.info("No stocks found below 50-day moving average. Try again later!")
    else:
        # Sort by how far below MA (largest discount first)
        sorted_opportunities = sorted(dip_opportunities, key=lambda x: x['below_ma'], reverse=True)
        
        for opp in sorted_opportunities:
            # Parse guru analysis
            lines = opp['analysis'].split('\n')
            verdict = next((l for l in lines if l.startswith("✅ VERDICT")), "✅ VERDICT: HOLD")
            target = next((l for l in lines if l.startswith("🎯 1-WEEK TARGET")), "🎯 1-WEEK TARGET: N/A")
            risk = next((l for l in lines if l.startswith("⚠️ KEY RISK")), "⚠️ KEY RISK: Market volatility")
            action = next((l for l in lines if l.startswith("💡 ACTION")), "💡 ACTION: Monitor")
            
            # Color-coded card
            color = "green" if "BUY" in verdict else "orange" if "HOLD" in verdict else "red"
            bg_color = "#f0fff0" if "BUY" in verdict else "#fffaf0" if "HOLD" in verdict else "#fff0f0"
            
            # Fixed: Properly formatted f-string (no indentation)
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
    <p style="margin: 5px 0;">{risk}</p>
    <p style="margin: 5px 0;">{action}</p>
    <p style="font-size: 0.8em; color: #666; margin: 5px 0;">
        50-MA: S${opp['ma_50']:.2f}
    </p>
</div>
""", unsafe_allow_html=True)
    
    status_text.text(f"Scan complete! Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption("💡 Tip: Refresh during SGX trading hours (9am-5pm SGT) for latest data")

# Footer
st.markdown("---")
st.markdown("📌 **How it works**: Scans all 30 STI stocks for 50-day MA breaches → Uses Groq AI for trading advice → Presents Netflix-style recommendations")
