import pandas as pd
from datetime import datetime

def log_trade(ticker: str, action: str, quantity: float, price: float, strategy: str):
    trade = {
        "timestamp": datetime.now().isoformat(),
        "ticker": ticker,
        "action": action,
        "quantity": quantity,
        "price": price,
        "value": quantity * price,
        "strategy": strategy
    }
    
    df = pd.DataFrame([trade])
    file_path = "outputs/trade_history.csv"
    
    if os.path.exists(file_path):
        df.to_csv(file_path, mode='a', header=False, index=False)
    else:
        df.to_csv(file_path, index=False)
    
    print(f"📝 Trade Logged → {action} {quantity} {ticker} @ ${price:.4f}")
