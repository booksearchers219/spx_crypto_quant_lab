import pandas as pd
import os
from datetime import datetime


def log_portfolio(bot_name: str, cash: float, total_value: float, positions: int, reset: bool = False):
    """
    Log portfolio state with consistent naming.
    Reset now only clears THIS bot's previous entries (keeps the other bot).
    """
    os.makedirs("outputs", exist_ok=True)
    log_file = "outputs/equity_log.csv"

    # Clean bot name
    if "crypto" in bot_name.lower():
        clean_name = "Crypto_Bot"
    elif "equity" in bot_name.lower() or "spx" in bot_name.lower():
        clean_name = "Equity_Bot"
    else:
        clean_name = bot_name

    # === RESET LOGIC: Only remove this bot's old entries ===
    if reset and os.path.exists(log_file):
        try:
            df = pd.read_csv(log_file)
            df = df[df['bot'] != clean_name]   # Keep the other bot
            if len(df) == 0:
                os.remove(log_file)
            else:
                df.to_csv(log_file, index=False)
            print(f"🗑️  RESET: Cleared previous entries for {clean_name} only")
        except:
            if os.path.exists(log_file):
                os.remove(log_file)

    # Prepare new row
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
    print(f"📊 Logged → {clean_name} | Value: ${total_value:,.2f} | Cash: ${cash:,.2f} | Total Cycles: {len(df_combined)}")