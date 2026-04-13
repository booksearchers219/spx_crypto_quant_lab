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
        df = df.sort_values('timestamp')

        # Get the SINGLE most recent record for each unique bot name
        latest = df.loc[df.groupby('bot')['timestamp'].idxmax()].reset_index(drop=True)

        total_cycles = len(df)  # Total log entries = total cycles across all bots

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

            # Count cycles for this specific bot
            bot_cycles = len(df[df['bot'] == row.get('bot')])

            pnl = total_value - initial
            pnl_pct = (pnl / initial * 100) if initial > 0 else 0.0

            print(f"   Initial     : ${initial:,.2f}")
            print(f"   Cash        : ${cash:,.2f}")
            print(f"   Value       : ${total_value:,.2f} | P&L: ${pnl:,.2f} ({pnl_pct:+.2f}%)")
            print(f"   Positions   : {positions}")
            print(f"   Cycles      : {bot_cycles:,}")
            print(f"   Last Updated: {last_updated}")
            print("-" * 100)
            print()

        # Overall summary
        print("=" * 120)
        print("📊 OVERALL DASHBOARD SUMMARY")
        print(f"   Total Combined Cycles : {total_cycles:,}")
        print(f"   Total Log Entries     : {len(df):,}")
        print(f"   Unique Bots Tracked   : {df['bot'].nunique()}")
        print(f"   Dashboard Generated   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 120)

    except Exception as e:
        print(f"⚠️ Error displaying dashboard: {e}")

    print("\nDashboard refreshed every 10 minutes.")


if __name__ == "__main__":
    show_dashboard()