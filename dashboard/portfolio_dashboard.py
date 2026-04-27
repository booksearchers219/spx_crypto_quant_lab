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
        print("⚠️ Log file not found. Run both bots with --reset.")
        return

    try:
        df = pd.read_csv(log_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.sort_values('timestamp')

        print(f"📊 Log contains {len(df)} entries | Unique bots: {df['bot'].nunique()}\n")

        # Latest record per bot
        latest = df.loc[df.groupby('bot')['timestamp'].idxmax()].reset_index(drop=True)

        print("📊 ACTIVE BOTS:\n")

        for _, row in latest.iterrows():
            bot_name = str(row.get('bot', 'Unknown'))
            cash = float(row.get('cash', 0.0))
            total_value = float(row.get('total_value', 0.0))
            positions = int(row.get('positions', 0))
            last_updated = row.get('timestamp', 'N/A')

            bot_cycles = len(df[df['bot'] == bot_name])

            pnl = total_value - 80000.0
            pnl_pct = (pnl / 80000.0 * 100) if 80000.0 > 0 else 0.0

            if 'crypto' in bot_name.lower():
                print("💰 CRYPTO BOT")
            elif 'equity' in bot_name.lower():
                print("📈 EQUITY BOT")
            else:
                print("🤖 BOT")

            print(f"   Name        : {bot_name}")
            print(f"   Initial     : $80,000.00")
            print(f"   Cash        : ${cash:,.2f}")
            print(f"   Value       : ${total_value:,.2f} | P&L: ${pnl:,.2f} ({pnl_pct:+.2f}%)")
            print(f"   Positions   : {positions}")
            print(f"   Cycles      : {bot_cycles:,}")
            print(f"   Last Updated: {last_updated}")
            print("-" * 110)
            print()

        # print("=" * 110)

    except Exception as e:
        print(f"⚠️ Error: {e}")

if __name__ == "__main__":
    show_dashboard()