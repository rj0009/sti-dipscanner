import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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

def create_session_with_retries():
    """Create a requests session with retry strategy"""
    st.write("DEBUG: Creating session with retry strategy...")
    session = requests.Session()
    
    # Define retry strategy
    retry_strategy = Retry(
        total=3,  # Total number of retries
        backoff_factor=1,  # Backoff factor for exponential backoff
        status_forcelist=[429, 500, 502, 503, 504],  # HTTP status codes to retry
    )
    
    # Mount adapter with retry strategy
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Add headers to mimic browser
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    
    st.write("DEBUG: Session created with headers:")
    for key, value in session.headers.items():
        st.write(f"  {key}: {value}")
        
    return session

def test_yahoo_connection():
    """Test connection to Yahoo Finance"""
    st.write("\nDEBUG: === TESTING YAHOO FINANCE CONNECTION ===")
    try:
        session = create_session_with_retries()
        response = session.get("https://finance.yahoo.com", timeout=10)
        st.write(f"DEBUG: Connection test response status: {response.status_code}")
        st.write(f"DEBUG: Response headers: {dict(response.headers)}")
        st.write(f"DEBUG: First 500 chars of response: {response.text[:500]}")
        
        if response.status_code == 200:
            st.success("✅ Yahoo Finance connection successful")
            return True
        else:
            st.error(f"❌ Yahoo Finance connection failed with status {response.status_code}")
            return False
    except Exception as e:
        st.error(f"❌ Connection test failed with exception: {str(e)}")
        return False

def get_stock_data(ticker):
    """Fetch data using yfinance with comprehensive debugging"""
    st.write(f"\nDEBUG: === FETCHING DATA FOR {ticker} ===")
    
    try:
        # Create session
        session = create_session_with_retries()
        
        # Test if ticker page exists
        st.write(f"DEBUG: Testing if ticker {ticker} exists...")
        ticker_url = f"https://finance.yahoo.com/quote/{ticker}"
        response = session.get(ticker_url, timeout=10)
        st.write(f"DEBUG: Ticker page response status: {response.status_code}")
        
        if response.status_code != 200:
            st.write(f"DEBUG: Non-200 response for ticker page: {response.text[:300]}")
            return None, None
            
        # Check for blocking indicators
        response_text = response.text.lower()
        if any(blocked in response_text for blocked in ['captcha', 'cloudflare', 'blocked', 'access denied']):
            st.write("DEBUG: WARNING - Yahoo is showing blocking page (CAPTCHA/Cloudflare)")
            st.write(f"DEBUG: Response snippet: {response.text[:500]}")
            return None, None
            
        # Check if it's actually the right ticker
        if "symbol lookup" in response_text or "no results" in response_text:
            st.write(f"DEBUG: Ticker {ticker} not found on Yahoo Finance")
            return None, None
            
        st.write(f"DEBUG: Ticker {ticker} appears to exist")
        
        # Now try to get historical data
        st.write(f"DEBUG: Attempting to get historical data for {ticker}...")
        stock = yf.Ticker(ticker, session=session)
        
        # Try different periods if needed
        periods_to_try = ["50d", "60d", "3mo"]
        for period in periods_to_try:
            st.write(f"DEBUG: Trying period '{period}' for {ticker}")
            try:
                hist = stock.history(period=period, interval="1d", timeout=10)
                st.write(f"DEBUG: History shape for {ticker} ({period}): {hist.shape}")
                
                if not hist.empty and len(hist) >= 2:
                    st.write(f"DEBUG: Successfully retrieved data for {ticker}")
                    st.write(f"DEBUG: Latest prices: {hist['Close'].tail().tolist()}")
                    current_price = hist['Close'].iloc[-1]
                    return current_price, hist['Close'].tolist()
                else:
                    st.write(f"DEBUG: Empty or insufficient data for {ticker} with period {period}")
            except Exception as hist_e:
                st.write(f"DEBUG: Exception getting history for {ticker} with period {period}: {str(hist_e)}")
                continue
                
        st.write(f"DEBUG: Failed to get sufficient data for {ticker} with all periods")
        return None, None
        
    except Exception as e:
        st.write(f"DEBUG: Exception in get_stock_data for {ticker}: {str(e)}")
        st.write(f"DEBUG: Exception type: {type(e).__name__}")
        return None, None

def calculate_50_day_ma(prices):
    """Calculate 50-day moving average with debugging"""
    st.write(f"\nDEBUG: === CALCULATING 50-DAY MA ===")
    st.write(f"DEBUG: Input prices count: {len(prices)}")
    st.write(f"DEBUG: First 5 prices: {prices[:5] if len(prices) >= 5 else prices}")
    st.write(f"DEBUG: Last 5 prices: {prices[-5:] if len(prices) >= 5 else prices}")
    
    # Filter out NaN values
    valid_prices = [p for p in prices if pd.notna(p)]
    st.write(f"DEBUG: Valid (non-NaN) prices count: {len(valid_prices)}")
    
    if not valid_prices:
        st.write("DEBUG: No valid prices found, returning 0")
        return 0
    
    # Calculate MA
    if len(valid_prices) >= 50:
        # Use last 50 prices
        ma_50 = sum(valid_prices[-50:]) / 50
        st.write(f"DEBUG: Calculated 50-day MA: {ma_50}")
    else:
        # Use all available prices
        ma_50 = sum(valid_prices) / len(valid_prices)
        st.write(f"DEBUG: Calculated MA with {len(valid_prices)} days: {ma_50}")
        
    return ma_50

def guru_analysis(stock, price, below_ma, news):
    """Get Groq-powered trading advice with debugging"""
    st.write(f"\nDEBUG: === RUNNING GROQ ANALYSIS FOR {stock} ===")
    st.write(f"DEBUG: Price: {price}, Below MA: {below_ma}%, News: {news[:100]}...")
    
    import requests
    
    # Check if API key is set
    if not GROQ_KEY or GROQ_KEY == "your_groq_key_here" or "your_groq_key_here" in GROQ_KEY:
        st.write("DEBUG: GROQ_KEY not properly set")
        return "❌ GROQ_KEY not set properly. Go to Settings → Secrets"
    
    st.write("DEBUG: GROQ_KEY appears to be set")
    
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
    
    st.write("DEBUG: Sending request to Groq API...")
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", 
                               json=payload, headers=headers, timeout=30)
        st.write(f"DEBUG: Groq API response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()["choices"][0]["message"]["content"]
            st.write(f"DEBUG: Groq analysis successful")
            return result
        else:
            st.write(f"DEBUG: Groq API error: {response.text}")
            return f"❌ Groq API error: {response.status_code}"
            
    except Exception as e:
        st.write(f"DEBUG: Exception in Groq analysis: {str(e)}")
        return f"❌ Groq analysis failed: {str(e)}"

# Streamlit UI - DEBUG MODE
st.set_page_config(layout="wide", page_title="YK's STI DipScanner - DEBUG")
st.title("🎯 YK's STI DipScanner - DEBUG MODE")

# Display environment info
st.subheader("Environment Information")
try:
    import streamlit as st_env
    st.write(f"Streamlit version: {st_env.__version__}")
except:
    st.write("Streamlit version: Unknown")

try:
    import yfinance as yf_env
    st.write(f"yfinance version: {yf_env.__version__}")
except:
    st.write("yfinance version: Unknown")

try:
    import pandas as pd_env
    st.write(f"Pandas version: {pd_env.__version__}")
except:
    st.write("Pandas version: Unknown")

# Data disclaimer
st.caption("⚠️ Data delayed 15+ minutes per SGX policy | Personal use only | Not financial advice")

# Scan button
if st.button("🔍 Scan STI Stocks Now (DEBUG)"):
    st.subheader("1. Testing Environment")
    
    # Test Yahoo Finance connection
    yahoo_connected = test_yahoo_connection()
    
    if not yahoo_connected:
        st.error("❌ Cannot proceed without Yahoo Finance connection")
        st.stop()
    
    st.subheader("2. Scanning Individual Stocks")
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    dip_opportunities = []
    debug_logs = []
    failed_tickers = []
    
    for i, stock in enumerate(STI_STOCKS):
        status_text.text(f"Scanning {stock} ({i+1}/{len(STI_STOCKS)})")
        debug_logs.append(f"🔍 SCANNING: {stock}")
        
        current_price, close_prices = get_stock_data(stock)
        
        if current_price and close_prices and len(close_prices) >= 2:
            debug_logs.append(f"✅ SUCCESS: Retrieved data for {stock}")
            
            ma_50 = calculate_50_day_ma(close_prices)
            below_ma_pct = round(((ma_50 - current_price) / ma_50) * 100, 1)
            
            debug_logs.append(f"📊 DATA: {stock} - Price: S${current_price:.2f}, 50-MA: S${ma_50:.2f} ({below_ma_pct}% below)")
            
            # Check for dip (below 50-MA)
            if current_price < ma_50:
                debug_logs.append(f"🎯 DIP FOUND: {stock} is {below_ma_pct}% below 50-MA")
                
                # Get news summary
                try:
                    debug_logs.append(f"📰 Getting news for {stock}...")
                    stock_obj = yf.Ticker(stock, session=create_session_with_retries())
                    news = stock_obj.news
                    news_summary = " | ".join([item['title'] for item in news[:3]]) if news else "No recent news"
                    debug_logs.append(f"📰 News summary: {news_summary[:100]}...")
                except Exception as news_e:
                    news_summary = "News unavailable"
                    debug_logs.append(f"❌ News error for {stock}: {str(news_e)}")
                
                # Get guru analysis
                analysis = guru_analysis(stock, current_price, below_ma_pct, news_summary)
                debug_logs.append(f"🤖 AI Analysis: {analysis[:100]}...")
                
                dip_opportunities.append({
                    'stock': stock,
                    'price': current_price,
                    'ma_50': ma_50,
                    'below_ma': below_ma_pct,
                    'analysis': analysis
                })
            else:
                debug_logs.append(f"📈 NO DIP: {stock} is above 50-MA (S${current_price:.2f} vs S${ma_50:.2f})")
        else:
            debug_logs.append(f"❌ FAILED: No data retrieved for {stock}")
            failed_tickers.append(stock)
        
        progress_bar.progress((i + 1) / len(STI_STOCKS))
        time.sleep(1.5)  # Be gentle with Yahoo's servers
    
    # Display debug logs
    st.subheader("3. Detailed Debug Logs")
    for log in debug_logs:
        st.code(log)
    
    # Summary
    st.subheader("4. Scan Summary")
    success_count = sum(1 for log in debug_logs if "SUCCESS" in log)
    fail_count = len(failed_tickers)
    dip_count = len(dip_opportunities)
    
    st.write(f"✅ Successful data retrieval: {success_count} stocks")
    st.write(f"❌ Failed data retrieval: {fail_count} stocks")
    st.write(f"🎯 Stocks below 50-MA: {dip_count} stocks")
    
    if success_count > 0:
        st.success(f"At least {success_count} stocks retrieved successfully!")
    else:
        st.error("No stock data retrieved. Check the debug logs above.")
        
    if dip_count > 0:
        st.success(f"Found {dip_count} stocks below 50-day moving average!")
    else:
        st.info("No stocks currently below 50-day moving average.")
    
    # Show failed tickers
    if failed_tickers:
        st.subheader("5. Failed Tickers")
        st.write("These tickers failed to retrieve data:")
        for ticker in failed_tickers:
            st.code(ticker)
        st.write("This could be due to:")
        st.write("- Temporary Yahoo Finance issues")
        st.write("- Delisted or invalid tickers")
        st.write("- Network connectivity problems")
        st.write("- Rate limiting by Yahoo Finance")
    
    # Show dip opportunities if any
    if dip_opportunities:
        st.subheader("6. Dip Opportunities Found")
        # Sort by how far below MA (largest discount first)
        sorted_opportunities = sorted(dip_opportunities, key=lambda x: x['below_ma'], reverse=True)
        
        for opp in sorted_opportunities:
            st.markdown(f"""
<div style="border: 2px solid orange; border-radius: 10px; padding: 15px; margin: 10px 0; background-color: #fffaf0;">
    <h4>{opp['stock']} - S${opp['price']:.2f} (🔻{opp['below_ma']}%)</h4>
    <p><strong>50-MA:</strong> S${opp['ma_50']:.2f}</p>
    <p><strong>AI Analysis:</strong></p>
    <pre>{opp['analysis']}</pre>
</div>
""", unsafe_allow_html=True)
    
    status_text.text(f"Scan complete! Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.markdown("---")
st.markdown("📌 This debug version shows exactly what's happening with data retrieval and processing")
