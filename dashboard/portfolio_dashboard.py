import pandas as pd
import os
from datetime import datetime

def show_dashboard():
    print("=" * 120)
    print("                  COMBINED VIRTUAL TRADING DASHBOARD")
    print("=" * 120)
    print(f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    log_file = "logs/portfolio_log.csv"   # adjust if your logger uses a different name/path

    if not os.path.exists(log_file):
        print("⚠️ Log file not found yet.")
        print(f"   Expected: {os.path.abspath(log_file)}")
        print("   → Run the bots for a few cycles so logging starts.")
        print("   → Make sure `log_portfolio()` is being called successfully.")
        print("\nDashboard will refresh every 10 minutes.")
        return

    try:
        df = pd.read_csv(log_file)

        # Ensure timestamp column exists and is datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        else:
            # fallback if no timestamp column
            df['timestamp'] = pd.to_datetime('now')

        # Get the most recent record for each bot
        latest = df.loc[df.groupby('bot_name')['timestamp'].idxmax()]

        for _, row in latest.iterrows():
            bot_name = str(row.get('bot_name', 'Unknown')).upper()

            if 'CRYPTO' in bot_name or 'CALM' in bot_name:
                print("💰 CRYPTO BOT")
            else:
                print("📈 EQUITY BOT")

            initial = row.get('initial_capital', 30000)
            cash = row.get('cash', 0)
            total_value = row.get('total_value', 0)
            positions = int(row.get('positions_count', 0))
            last_updated = row.get('timestamp', 'N/A')

            pnl = total_value - initial
            pnl_pct = (pnl / initial * 100) if initial > 0 else 0

            print(f"   Initial : ${initial:,.2f}")
            print(f"   Cash    : ${cash:,.2f}")
            print(f"   Value   : ${total_value:,.2f} | P&L: ${pnl:,.2f} ({pnl_pct:+.2f}%)")
            print(f"   Positions : {positions}")
            print(f"   Last Updated: {last_updated}")
            print("-" * 80)

    except Exception as e:
        print(f"⚠️ Error reading dashboard data: {e}")
        print("   Check that the log file has the expected columns (bot_name, cash, total_value, positions_count, timestamp).")

    print("\nDashboard refreshed every 10 minutes.")


if __name__ == "__main__":
    show_dashboard()