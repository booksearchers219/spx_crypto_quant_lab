import pandas as pd
import os
from datetime import datetime


def log_portfolio(bot_name: str, cash: float, total_value: float, positions: int):
    """
    Log portfolio state with consistent naming
    """
    os.makedirs("outputs", exist_ok=True)
    log_file = "outputs/equity_log.csv"

    # Force clean consistent name for crypto bot
    if "crypto" in bot_name.lower():
        clean_name = "Crypto_Bot"
    elif "equity" in bot_name.lower() or "spx" in bot_name.lower():
        clean_name = "Equity_Bot"
    else:
        clean_name = bot_name

    data = {
        'timestamp': [datetime.now()],
        'bot': [clean_name],
        'cash': [round(float(cash), 2)],
        'total_value': [round(float(total_value), 2)],
        'positions': [int(positions)]
    }

    df_new = pd.DataFrame(data)

    if os.path.exists(log_file):
        try:
            df_existing = pd.read_csv(log_file)
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        except:
            df_combined = df_new
    else:
        df_combined = df_new

    df_combined.to_csv(log_file, index=False)
    print(f"📊 Logged → {clean_name} | Value: ${total_value:,.2f} | Cash: ${cash:,.2f}")