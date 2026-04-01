import json
import os
from datetime import datetime
from risk.risk_manager import RiskManager


def show_dashboard():
    print("\n" + "=" * 120)
    print(" " * 40 + "COMBINED VIRTUAL TRADING DASHBOARD")
    print("=" * 120)
    print(f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    total_initial = 60000.0
    total_value = 0.0
    total_pnl = 0.0

    for bot_name, rm_name in [("💰 CRYPTO BOT", "crypto"), ("📈 EQUITY BOT", "equity")]:
        try:
            rm = RiskManager(capital=30000, name=rm_name)
            # Use entry price for consistency with bot prints (less noisy)
            value = rm.cash
            for pos in rm.positions.values():
                value += pos['quantity'] * pos['entry_price']

            pnl = value - rm.initial_capital

            print(bot_name)
            print(f"   Initial     : ${rm.initial_capital:,.2f}")
            print(f"   Cash        : ${rm.cash:,.2f}")
            print(f"   Value       : ${value:,.2f} | P&L: ${pnl:,.2f} ({pnl / rm.initial_capital * 100:+.2f}%)")
            print(f"   Positions   : {len(rm.positions)}")

            if rm.trade_history:
                trades = pd.DataFrame(rm.trade_history)
                closed = trades[trades['action'] == 'SELL']
                wins = len(closed[closed['pnl'] > 0])
                win_rate = (wins / len(closed) * 100) if len(closed) > 0 else 0
                print(f"   Win Rate    : {win_rate:.1f}%")
                print(f"   Total Trades: {len(trades)}")

            total_value += value
            total_pnl += pnl
        except Exception as e:
            print(f"{bot_name} → Error: {e}")

        print("-" * 85)

    print("=" * 120)
    print(f"💎 COMBINED TOTAL")
    print(f"   Initial : $60,000.00")
    print(f"   Current : ${total_value:,.2f}")
    print(f"   P&L     : ${total_pnl:,.2f} ({total_pnl / total_initial * 100:+.2f}%)")
    print("=" * 120)

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