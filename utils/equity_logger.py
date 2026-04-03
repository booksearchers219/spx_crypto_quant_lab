import pandas as pd
import os
from datetime import datetime


def log_portfolio(bot_name: str, cash: float, total_value: float, positions_count: int, unrealized_pnl: float = 0.0):
    """Log portfolio state for graphing and dashboard"""
    log_entry = {
        "timestamp": datetime.now(),
        "bot": bot_name,  # keep consistent with dashboard
        "cash": round(float(cash), 2),
        "total_value": round(float(total_value), 2),
        "positions": positions_count,
        "unrealized_pnl": round(float(unrealized_pnl), 2),
        "total_pnl": round(float(total_value - 30000), 2)
    }

    log_df = pd.DataFrame([log_entry])
    log_file = "outputs/equity_log.csv"

    if os.path.exists(log_file):
        log_df.to_csv(log_file, mode='a', header=False, index=False)
    else:
        log_df.to_csv(log_file, index=False)

    print(f"📊 Logged → {bot_name} | Value: ${total_value:,.2f} | P&L: ${log_entry['total_pnl']:,.2f}")