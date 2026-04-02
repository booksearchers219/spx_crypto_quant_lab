import pandas as pd
import os
import json
from datetime import datetime


def show_dashboard():
    print("\n" + "=" * 120)
    print(" " * 40 + "COMBINED VIRTUAL TRADING DASHBOARD")
    print("=" * 120)
    print(f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    log_file = "outputs/equity_log.csv"
    total_initial = 60000.0
    total_value = 0.0
    total_pnl = 0.0

    if os.path.exists(log_file):
        df = pd.read_csv(log_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Get latest entry for each bot
        latest = df.groupby('bot').last().reset_index()

        for _, row in latest.iterrows():
            bot_name = row['bot']
            value = row['total_value']
            pnl = row['total_pnl']

            if bot_name == "Crypto":
                print(f"💰 CRYPTO BOT")
            else:
                print(f"📈 EQUITY BOT")

            print(f"   Initial     : $30,000.00")
            print(f"   Cash        : ${row['cash']:,.2f}")
            print(f"   Value       : ${value:,.2f} | P&L: ${pnl:,.2f} ({pnl / 30000 * 100:+.2f}%)")
            print(f"   Positions   : {int(row['positions'])}")
            print(f"   Last Updated: {row['timestamp']}")

            total_value += value
            total_pnl += pnl

    else:
        print("⚠️ No equity_log.csv found yet. Run the bots for a while.")

    # If one bot is missing, show placeholder
    if total_value == 0:
        print("💰 CRYPTO BOT → No data yet")
        print("📈 EQUITY BOT → No data yet")

    print("=" * 120)
    print(f"💎 COMBINED TOTAL")
    print(f"   Initial : $60,000.00")
    print(f"   Current : ${total_value:,.2f}")
    print(f"   P&L     : ${total_pnl:,.2f} ({total_pnl / total_initial * 100:+.2f}%)")
    print("=" * 120)

    # Research Status
    try:
        with open("outputs/latest_best.json") as f:
            best = json.load(f)
            print(f"\n🔬 Latest Research : {best.get('timestamp', 'Unknown')} | Mode: {best.get('mode', 'Unknown')}")
            print("Top Tickers:", ", ".join(best.get('top_tickers', [])[:8]))
    except:
        print("\n⚠️ No research file found")

    print("\nRefresh with: python -m main --mode dashboard")
    print("=" * 120)


if __name__ == "__main__":
    show_dashboard()