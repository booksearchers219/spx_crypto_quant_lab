import pandas as pd
import os
from datetime import datetime


def show_dashboard():
    print("=" * 110)
    print("                  COMBINED VIRTUAL TRADING DASHBOARD")
    print("=" * 110)
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

        total_cycles = len(df)

        print("📊 ACTIVE BOTS:\n")

        for _, row in latest.iterrows():
            bot_name = str(row.get('bot', 'Unknown'))
            cash = float(row.get('cash', 0.0))
            total_value = float(row.get('total_value', 0.0))
            positions = int(row.get('positions', 0))
            last_updated = row.get('timestamp', 'N/A')

            # Count total cycles for this bot
            bot_cycles = len(df[df['bot'] == bot_name])

            pnl = total_value - 30000.0
            pnl_pct = (pnl / 30000.0 * 100) if 30000.0 > 0 else 0.0

            # === Better Bot Type Detection ===
            if 'crypto' in bot_name.lower():
                print("💰 CRYPTO BOT")
                print(f"   Name        : {bot_name}")
            elif 'equity' in bot_name.lower() or 'spx' in bot_name.lower():
                print("📈 EQUITY BOT")
                print(f"   Name        : {bot_name}")
            else:
                print("🤖 BOT")
                print(f"   Name        : {bot_name}")

            print(f"   Initial     : $30,000.00")
            print(f"   Cash        : ${cash:,.2f}")
            print(f"   Value       : ${total_value:,.2f} | P&L: ${pnl:,.2f} ({pnl_pct:+.2f}%)")
            print(f"   Positions   : {positions}")
            print(f"   Cycles      : {bot_cycles:,}")
            print(f"   Last Updated: {last_updated}")
            print("-" * 110)
            print()

        # Overall Summary
        print("=" * 110)
        print("📊 OVERALL DASHBOARD SUMMARY")
        print(f"   Total Combined Cycles : {total_cycles:,}")
        print(f"   Unique Bots Tracked   : {df['bot'].nunique()}")
        print(f"   Dashboard Generated   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 110)

    except Exception as e:
        print(f"⚠️ Error displaying dashboard: {e}")

    print("\nDashboard refreshed every 10 minutes.")


if __name__ == "__main__":
    show_dashboard()