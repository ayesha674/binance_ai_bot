import json
import os
from datetime import datetime
import config

DATA_FILE = "paper_portfolio.json"

def load_portfolio():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {
        "usdt_balance": config.INITIAL_PAPER_BALANCE,
        "btc_balance": 0.0,
        "buy_price": 0.0,
        "in_position": False,
        "trade_history": []
    }

def save_portfolio(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def calculate_pnl_stats(history):
    total_pnl = 0.0
    wins = 0
    losses = 0
    
    for trade in history:
        if trade.get("Type") == "SELL":
            pnl_val = float(trade.get("PnL_Raw", 0.0))
            total_pnl += pnl_val
            if pnl_val > 0:
                wins += 1
            elif pnl_val < 0:
                losses += 1

    total_closed = wins + losses
    win_rate = round((wins / total_closed) * 100, 1) if total_closed > 0 else 0.0
    return round(total_pnl, 2), wins, losses, win_rate

def execute_trade(signal, current_price, symbol="BTC/USDT"):
    portfolio = load_portfolio()
    if "trade_history" not in portfolio:
        portfolio["trade_history"] = []
        
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Stop Loss / Take Profit Check
    if portfolio["in_position"]:
        buy_price = portfolio["buy_price"]
        price_change_pct = ((current_price - buy_price) / buy_price) * 100
        
        if price_change_pct <= -config.STOP_LOSS_PERCENT:
            signal = "SELL"
        elif price_change_pct >= config.TAKE_PROFIT_PERCENT:
            signal = "SELL"

    # BUY Execution
    if signal == "BUY" and not portfolio["in_position"]:
        amount_to_spend = min(config.MAX_TRADE_AMOUNT, portfolio["usdt_balance"])
        if amount_to_spend >= 10:
            btc_bought = amount_to_spend / current_price
            portfolio["usdt_balance"] -= amount_to_spend
            portfolio["btc_balance"] += btc_bought
            portfolio["buy_price"] = current_price
            portfolio["in_position"] = True
            
            portfolio["trade_history"].insert(0, {
                "Time": now, "Type": "BUY", "Symbol": symbol, 
                "Price": f"${current_price}", "Amount": round(btc_bought, 6), "PnL": "-", "PnL_Raw": 0.0
            })
            save_portfolio(portfolio)

    # SELL Execution
    elif signal == "SELL" and portfolio["in_position"]:
        usdt_received = portfolio["btc_balance"] * current_price
        profit_loss = usdt_received - (portfolio["btc_balance"] * portfolio["buy_price"])
        
        portfolio["usdt_balance"] += usdt_received
        
        portfolio["trade_history"].insert(0, {
            "Time": now, "Type": "SELL", "Symbol": symbol, 
            "Price": f"${current_price}", "Amount": round(portfolio["btc_balance"], 6), 
            "PnL": f"${round(profit_loss, 2)}", "PnL_Raw": profit_loss
        })
        
        portfolio["btc_balance"] = 0.0
        portfolio["buy_price"] = 0.0
        portfolio["in_position"] = False
        save_portfolio(portfolio)

    return portfolio