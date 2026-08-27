import pandas as pd

def calculate_indicators(ohlcv):
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # EMAs
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    return df

def analyze_market_signal(ohlcv_15m, ohlcv_1h):
    df_15m = calculate_indicators(ohlcv_15m)
    df_1h = calculate_indicators(ohlcv_1h)

    latest_15m = df_15m.iloc[-1]
    latest_1h = df_1h.iloc[-1]

    price = float(latest_15m['close'])
    rsi_15m = round(float(latest_15m['rsi']), 2) if not pd.isna(latest_15m['rsi']) else 50.0
    ema_20_15m = float(latest_15m['ema_20'])
    ema_50_15m = float(latest_15m['ema_50'])

    # 1-Hour Trend Direction
    trend_1h = "UPTREND" if latest_1h['ema_20'] > latest_1h['ema_50'] else "DOWNTREND"

    # Multi-Timeframe Logic
    # BUY: 1h Uptrend + 15m RSI oversold & 15m EMA crossover
    # SELL: 1h Downtrend + 15m RSI overbought
    if trend_1h == "UPTREND" and rsi_15m < 45 and ema_20_15m > ema_50_15m:
        signal = "BUY"
    elif trend_1h == "DOWNTREND" and (rsi_15m > 60 or ema_20_15m < ema_50_15m):
        signal = "SELL"
    else:
        signal = "HOLD"

    return {
        'price': price,
        'rsi': rsi_15m,
        'ema_20': round(ema_20_15m, 2),
        'ema_50': round(ema_50_15m, 2),
        'trend_1h': trend_1h,
        'signal': signal
    }