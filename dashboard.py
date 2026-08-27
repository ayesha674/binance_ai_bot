import os
import time
import requests
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import ccxt
from dotenv import load_dotenv
import config
from strategy import analyze_market_signal
from trader import execute_trade, calculate_pnl_stats

load_dotenv()

st.set_page_config(
    page_title="Crypto AI Trading Console", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Mobile Responsive & Touch-Friendly CSS UI
st.markdown("""
    <style>
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 0.3rem !important;
            padding-right: 0.3rem !important;
            padding-top: 0.5rem !important;
            padding-bottom: 2rem !important;
        }
        
        [data-testid="stMetric"] {
            background-color: #1e222d;
            padding: 8px 12px !important;
            border-radius: 8px;
            margin-bottom: 6px !important;
            border: 1px solid #2a2e39;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.1rem !important;
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.75rem !important;
        }
        
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
            margin-bottom: 0.3rem !important;
        }
        
        .js-plotly-plot {
            width: 100% !important;
        }
        
        [data-testid="stPopover"] {
            position: fixed !important;
            bottom: 20px !important;
            right: 15px !important;
            z-index: 999999 !important;
            width: auto !important;
        }
        [data-testid="stPopover"] button {
            background-color: #2962ff !important;
            color: white !important;
            border-radius: 25px !important;
            padding: 10px 18px !important;
            box-shadow: 0px 4px 12px rgba(0,0,0,0.4) !important;
            border: none !important;
            font-weight: bold !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# Fetch API Keys from Secrets (Streamlit Cloud) or .env (Local)
api_key = st.secrets.get("BINANCE_API_KEY", os.getenv('BINANCE_API_KEY'))
secret_key = st.secrets.get("BINANCE_SECRET_KEY", os.getenv('BINANCE_SECRET_KEY'))
gemini_key = st.secrets.get("GEMINI_API_KEY", os.getenv('GEMINI_API_KEY'))

# Binance exchange connection with public data endpoint fix for US Cloud Servers
exchange = ccxt.binance({
    'apiKey': api_key, 
    'secret': secret_key,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'spot', 
        'adjustForTimeDifference': True, 
        'recvWindow': 60000
    },
    'urls': {
        'api': {
            'public': 'https://data-api.binance.vision/api/v3',
        }
    }
})

# Sidebar Controls
with st.sidebar:
    st.header("⚡ Bot Controls")
    st.divider()
    selected_pair = st.selectbox("Select Crypto Pair", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
    st.divider()
    mode_text = "DEMO / PAPER" if config.PAPER_TRADING else "REAL TRADING"
    st.info(f"**Mode:** {mode_text}")
    st.write(f"**Max Per Trade:** ${config.MAX_TRADE_AMOUNT}")
    st.write(f"**Stop Loss:** {config.STOP_LOSS_PERCENT}%")
    st.write(f"**Take Profit:** {config.TAKE_PROFIT_PERCENT}%")

try:
    ohlcv_15m = exchange.fetch_ohlcv(selected_pair, timeframe='15m', limit=60)
    ohlcv_1h = exchange.fetch_ohlcv(selected_pair, timeframe='1h', limit=60)
    
    analysis = analyze_market_signal(ohlcv_15m, ohlcv_1h)

    def trigger_manual_buy(price_val, pair_val):
        execute_trade("BUY", price_val, symbol=pair_val)

    def trigger_manual_sell(price_val, pair_val):
        execute_trade("SELL", price_val, symbol=pair_val)

    portfolio = execute_trade(analysis['signal'], analysis['price'], symbol=selected_pair)

    st.title("⚡ AI Trading Console")
    st.caption(f"15m + 1h Strategy • {selected_pair}")

    # Key Metrics Display
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("PRICE", f"${analysis['price']}")
    m2.metric("1H TREND", analysis['trend_1h'])
    m3.metric("RSI (15m)", analysis['rsi'])
    m4.metric("EMA 20", f"${analysis['ema_20']}")
    m5.metric("SIGNAL", analysis['signal'])

    st.divider()

    # Action Controls
    st.subheader("🛠️ Manual Testing")
    btn_col1, btn_col2 = st.columns(2)
    
    with btn_col1:
        st.button("🚀 Force BUY", use_container_width=True, type="primary", on_click=trigger_manual_buy, args=(analysis['price'], selected_pair))

    with btn_col2:
        st.button("🔴 Force SELL", use_container_width=True, on_click=trigger_manual_sell, args=(analysis['price'], selected_pair))

    st.divider()

    # Performance
    history = portfolio.get("trade_history", [])
    total_pnl, wins, losses, win_rate = calculate_pnl_stats(history)

    st.subheader("📊 Performance")
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Net PnL", f"${total_pnl}")
    p2.metric("Wins", f"{wins}")
    p3.metric("Losses", f"{losses}")
    p4.metric("Win Rate", f"{win_rate}%")

    st.divider()

    # Candlestick Chart (Mobile-Optimized Height)
    df = pd.DataFrame(ohlcv_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        name="Price", increasing_line_color='#00c087', decreasing_line_color='#ff3b30'
    ))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['ema_20'], mode='lines', name='EMA 20', line=dict(color='#ffb703', width=1.5)))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['ema_50'], mode='lines', name='EMA 50', line=dict(color='#2196f3', width=1.5)))

    fig.update_layout(
        template="plotly_dark", 
        xaxis_rangeslider_visible=False,
        height=320, 
        margin=dict(l=5, r=5, t=25, b=10),
        paper_bgcolor='#131722', 
        plot_bgcolor='#131722',
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1, font=dict(size=10))
    )

    st.plotly_chart(fig, use_container_width=True, config={'responsive': True, 'displayModeBar': False})

    # Portfolio Info
    st.subheader("💼 Live Wallet")
    w1, w2, w3 = st.columns(3)
    w1.metric("USDT", f"${round(portfolio['usdt_balance'], 2)}")
    w2.metric("Crypto", f"{round(portfolio['btc_balance'], 6)}")
    w3.metric("Entry Price", f"${portfolio['buy_price']}" if portfolio['in_position'] else "None")

    # Executed History
    st.divider()
    st.subheader("📜 Executed Trades")
    if history:
        display_df = pd.DataFrame(history).drop(columns=['PnL_Raw'], errors='ignore')
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No trades executed yet.")

    # Floating AI Assistant Button
    popover = st.popover("💬 AI Chat", use_container_width=True)

    with popover:
        st.subheader("🤖 AI Assistant")
        
        if "messages" not in st.session_state:
            st.session_state.messages = []

        chat_container = st.container(height=300)
        with chat_container:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        user_input = st.chat_input("Poochhein market ke baare mein...")

        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(user_input)

            if not gemini_key:
                reply = "⚠️ Please set GEMINI_API_KEY in Streamlit Secrets / .env file."
            else:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={gemini_key}"
                    
                    system_context = f"""
                    You are a smart crypto AI trading assistant embedded in a trading bot dashboard.
                    Current Live Context:
                    - Selected Pair: {selected_pair}
                    - Live Price: ${analysis['price']}
                    - 1H Market Trend: {analysis['trend_1h']}
                    - 15m RSI: {analysis['rsi']}
                    - AI Signal: {analysis['signal']}
                    - Wallet USDT Balance: ${round(portfolio['usdt_balance'], 2)}
                    - In Position: {portfolio['in_position']}
                    
                    Answer concisely in Roman Urdu or English.
                    """
                    
                    payload = {
                        "contents": [{
                            "parts": [{"text": f"{system_context}\nUser Question: {user_input}"}]
                        }]
                    }
                    
                    response = requests.post(url, json=payload)
                    res_data = response.json()
                    
                    if response.status_code == 200:
                        reply = res_data['candidates'][0]['content']['parts'][0]['text']
                    else:
                        reply = f"API Error: {res_data.get('error', {}).get('message', 'Unknown error')}"

                except Exception as err:
                    reply = f"Error generating response: {err}"

            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.rerun()

except Exception as e:
    st.error(f"⚠️ Error fetching live data: {e}")

time.sleep(30)
st.rerun()run()
