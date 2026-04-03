import pandas as pd
import os
from datetime import datetime

def show_dashboard():
    print("=" * 120)
    print("                  COMBINED VIRTUAL TRADING DASHBOARD")
    print("=" * 120)
    print(f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    log_file = "outputs/equity_log.csv"

    if not os.path.exists(log_file):
        print("⚠️ Log file not found yet. Run the bots for a few cycles.")
        return

    try:
        df = pd.read_csv(log_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

        # Get the SINGLE most recent record for each unique bot name
        latest = df.loc[df.groupby('bot')['timestamp'].idxmax()].reset_index(drop=True)

        for _, row in latest.iterrows():
            bot_name = str(row.get('bot', 'Unknown')).upper()

            if 'CRYPTO' in bot_name or 'CALM' in bot_name:
                print("💰 CRYPTO BOT")
            else:
                print("📈 EQUITY BOT")

            initial = 30000.0
            cash = row.get('cash', 0.0)
            total_value = row.get('total_value', 0.0)
            positions = int(row.get('positions', 0))
            last_updated = row.get('timestamp', 'N/A')

            pnl = total_value - initial
            pnl_pct = (pnl / initial * 100) if initial > 0 else 0.0

            print(f"   Initial : ${initial:,.2f}")
            print(f"   Cash    : ${cash:,.2f}")
            print(f"   Value   : ${total_value:,.2f} | P&L: ${pnl:,.2f} ({pnl_pct:+.2f}%)")
            print(f"   Positions : {positions}")
            print(f"   Last Updated: {last_updated}")
            print("-" * 100)
            print()

    except Exception as e:
        print(f"⚠️ Error displaying dashboard: {e}")

    print("Dashboard refreshed every 10 minutes.")


if __name__ == "__main__":
    show_dashboard()