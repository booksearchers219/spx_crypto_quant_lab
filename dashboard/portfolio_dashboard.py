import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
import os
import pandas as pd
from datetime import datetime
from risk.risk_manager import RiskManager

def show_dashboard():
    print("\n" + "="*110)
    print(" " * 35 + "COMBINED VIRTUAL TRADING DASHBOARD")
    print("="*110)
    print(f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    total_initial = 60000.0   # 30k crypto + 30k equity
    total_value = 0.0
    total_pnl = 0.0

    # Load Crypto Portfolio
    try:
        rm_crypto = RiskManager(capital=30000, name="crypto")
        value_crypto = rm_crypto.get_current_value({})  # We don't have live prices here, use entry for simplicity
        pnl_crypto = value_crypto - rm_crypto.initial_capital
        print(f"💰 CRYPTO BOT")
        print(f"   Initial : ${rm_crypto.initial_capital:,.2f}")
        print(f"   Cash    : ${rm_crypto.cash:,.2f}")
        print(f"   Value   : ${value_crypto:,.2f} | P&L: ${pnl_crypto:,.2f} ({pnl_crypto/rm_crypto.initial_capital*100:+.2f}%)")
        print(f"   Positions: {len(rm_crypto.positions)}")
        total_value += value_crypto
        total_pnl += pnl_crypto
    except:
        print("💰 CRYPTO BOT → No data yet")

    print("-" * 60)

    # Load Equity Portfolio
    try:
        rm_equity = RiskManager(capital=30000, name="equity")
        value_equity = rm_equity.get_current_value({})
        pnl_equity = value_equity - rm_equity.initial_capital
        print(f"📈 EQUITY BOT")
        print(f"   Initial : ${rm_equity.initial_capital:,.2f}")
        print(f"   Cash    : ${rm_equity.cash:,.2f}")
        print(f"   Value   : ${value_equity:,.2f} | P&L: ${pnl_equity:,.2f} ({pnl_equity/rm_equity.initial_capital*100:+.2f}%)")
        print(f"   Positions: {len(rm_equity.positions)}")
        total_value += value_equity
        total_pnl += pnl_equity
    except:
        print("📈 EQUITY BOT → No data yet")

    print("="*110)
    print(f"💎 COMBINED TOTAL")
    print(f"   Initial : $60,000.00")
    print(f"   Current : ${total_value:,.2f}")
    print(f"   P&L     : ${total_pnl:,.2f} ({total_pnl/total_initial*100:+.2f}%)")
    print("="*110)

    # Research Status
    try:
        with open("outputs/latest_best.json") as f:
            best = json.load(f)
            print(f"\n🔬 Latest Research : {best.get('timestamp', 'Unknown')} | Mode: {best.get('mode', 'Unknown')}")
            print("Top Tickers:", ", ".join(best.get('top_tickers', [])[:8]))
    except:
        print("\n⚠️ No research file found")

    print("\nRefresh with: python -m main --mode dashboard")
    print("="*110)


if __name__ == "__main__":
    show_dashboard()