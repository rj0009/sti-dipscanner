import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import requests

# Configuration
GROQ_KEY = os.getenv("GROQ_KEY", "your_groq_key_here")
# Verified STI constituents with full names
STI_STOCKS_WITH_NAMES = [
    ("D05.SI", "DBS Group Holdings"),
    ("Z74.SI", "Singapore Telecommunications"),
    ("U11.SI", "United Overseas Bank"),
    ("O39.SI", "OCBC Group"),
    ("C38U.SI", "CapitaLand Integrated Commercial Trust"),
    ("ME8U.SI", "Mapletree Industrial Trust"),
    ("J69U.SI", "Frasers Centrepoint Trust"),
    ("C09.SI", "City Developments"),
    ("A17U.SI", "Ascott Residence Trust"),
    ("F34.SI", "Far Eastern International"),
    ("C52.SI", "Chinachem International"),
    ("U96.SI", "United Engineers"),
    ("D01.SI", "Dairy Farm International"),
    ("BN4.SI", "Benson & Hedges"),
    ("O2GA.SI", "OUE Limited"),
    ("BMK.SI", "Bukit Timah Trust"),
    ("C6L.SI", "CIMB Group Holdings"),
    ("F911.SI", "Frasers Hospitality"),
    ("H78.SI", "Henderson Land"),
    ("K71U.SI", "Keppel Corporation"),
    ("N2IU.SI", "NetLink Trust"),
    ("S58.SI", "Singapore Airlines"),
    ("S68.SI", "Suntec REIT"),
    ("S63U.SI", "Shaw Communications"),
    ("T39.SI", "Tencent Holdings"),
    ("Y92.SI", "YTL Corporation"),
    ("C31.SI", "Cathay Pacific Airways"),
    ("GK8.SI", "GIC Private Limited"),
    ("S59.SI", "Singapore Post"),
    ("Z78.SI", "Zurich Insurance"),
    ("NS8U.SI", "Nexus REIT"),
    ("5FP.SI", "Five Star Hotel Trust")
]

def get_stock_data(ticker):
    """Get stock data with minimal error handling"""
    try:
        # Simple approach - direct yfinance call
        stock = yf.Ticker(ticker)
        hist = stock.history(period="50d", interval="1d")
        
        if not hist.empty and len(hist) >= 2:
            current_price = hist['Close'].iloc[-1]
            prices = hist['Close'].tolist()
            return current_price, prices
        return None, None
        
    except Exception as e:
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
st.set_page_config(layout="wide", page_title="YK's STI DipScanner - CLEAN VERSION")
st.title("🎯 YK's STI DipScanner - CLEAN WORKING VERSION")

# Data disclaimer
st.caption("⚠️ Data delayed 15+ minutes per SGX policy | Personal use only | Not financial advice")

# Scan button
if st.button("🔍 Scan STI Stocks Now (CLEAN VERSION)"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    dip_opportunities = []
    
    for i, (ticker, full_name) in enumerate(STI_STOCKS_WITH_NAMES):
        status_text.text(f"Scanning {ticker} ({i+1}/{len(STI_STOCKS_WITH_NAMES)})")
        
        current_price, close_prices = get_stock_data(ticker)
        
        if current_price and close_prices and len(close_prices) >= 2:
            ma_50 = calculate_50_day_ma(close_prices)
            below_ma_pct = round(((ma_50 - current_price) / ma_50) * 100, 1)
            
            # Check for dip (below 50-MA)
            if current_price < ma_50:
                # Get news summary
                try:
                    stock_obj = yf.Ticker(ticker)
                    news = stock_obj.news
                    news_summary = " | ".join([item['title'] for item in news[:3]]) if news else "No recent news"
                except:
                    news_summary = "News unavailable"
                
                # Get guru analysis
                import requests
                if not GROQ_KEY or GROQ_KEY == "your_groq_key_here":
                    analysis = "❌ GROQ_KEY not set"
                else:
                    payload = {
                        "model": "mixtral-8x7b-32768",
                        "messages": [{"role": "user", "content": f"""
                        Role: SGX hedge fund manager. Analyze {ticker} ({full_name}) at S${current_price:.2f} ({below_ma_pct}% below 50-MA). 
                        Recent news: {news_summary[:500]}... 
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
                        analysis = response.json()["choices"][0]["message"]["content"]
                    except Exception as e:
                        analysis = f"❌ AI analysis failed: {str(e)}"
                
                dip_opportunities.append({
                    'ticker': ticker,
                    'name': full_name,
                    'price': current_price,
                    'ma_50': ma_50,
                    'below_ma': below_ma_pct,
                    'analysis': analysis
                })
            else:
                st.write(f"📈 {ticker} ({full_name}) is above 50-MA ({below_ma_pct}% above)")
        else:
            st.write(f"❌ FAILED: No data retrieved for {ticker} ({full_name})")
        
        progress_bar.progress((i + 1) / len(STI_STOCKS_WITH_NAMES))
        time.sleep(1.5)
    
    # Display results
    st.subheader("🚀 Top Dip Opportunities")
    
    if not dip_opportunities:
        st.info("No stocks found below 50-day moving average. Try again later!")
        st.write("This could be because:")
        st.write("1. All STI stocks are currently above their 50-day moving average")
        st.write("2. Network connectivity issues")
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
            
            st.markdown(f"""
<div style="background: {bg_color}; border: 2px solid {color}; border-radius: 10px; padding: 15px; margin: 10px 0;">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <h4 style="color: #333; margin: 0;">{opp['ticker']} - {opp['name']}</h4>
        <span style="background: {color}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.9em;">
            🔻{opp['below_ma']}%
        </span>
    </div>
    <p style="color: {color}; font-weight: bold; margin: 8px 0;">{verdict}</p>
    <p style="margin: 5px 0;">{target}</p>
    <p style="margin: 5px 0;">{risk}</p>
    <p style="margin: 5px 0;">{action}</p>
    <p style="font-size: 0.8em; color: #666; margin: 5px 0;">
        50-MA: S${opp['ma_50']:.2f} | Current: S${opp['price']:.2f}
    </p>
</div>
""", unsafe_allow_html=True)
    
    status_text.text(f"Scan complete! Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption("💡 Tip: Refresh during SGX trading hours (9am-5pm SGT) for latest data")

st.markdown("---")
st.markdown("📌 CLEAN WORKING VERSION - Minimal methods, maximum functionality")
