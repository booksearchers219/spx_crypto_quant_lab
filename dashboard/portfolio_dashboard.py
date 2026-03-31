import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
import os
import pandas as pd
from datetime import datetime
from risk.risk_manager import RiskManager

def show_dashboard():
    print("\n" + "="*100)
    print(" " * 32 + "RESEARCH-DRIVEN VIRTUAL TRADING DASHBOARD")
    print("="*100)
    print(f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    rm = RiskManager(capital=30000)
    total_value = rm.cash + sum(p['quantity'] * p['entry_price'] for p in rm.positions.values())
    pnl = total_value - rm.initial_capital

    print(f"💰 Initial      : ${rm.initial_capital:,.2f}")
    print(f"💵 Cash         : ${rm.cash:,.2f}")
    print(f"🏦 Total Value  : ${total_value:,.2f}   |   P&L: ${pnl:,.2f} ({pnl/rm.initial_capital*100:+.2f}%)")

    # Research Status
    try:
        with open("outputs/latest_best.json") as f:
            best = json.load(f)
            print(f"\n🔬 Latest Research : {best['timestamp']} | Top {len(best['top_tickers'])} tickers being traded")
            print("Top Research Tickers:", ", ".join(best['top_tickers'][:6]))
    except:
        print("\n⚠️ No research file yet — run research first")

    # Chart
    if rm.trade_history:
        plt.figure(figsize=(14, 6))
        equity = [rm.initial_capital]
        for t in rm.trade_history:
            equity.append(equity[-1] + t.get('pnl', 0))
        plt.plot(equity, linewidth=2.5)
        plt.title("Portfolio Equity Curve (Research-Driven)")
        plt.xlabel("Trade Count")
        plt.ylabel("Portfolio Value ($)")
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig("outputs/charts/dashboard_equity_curve.png", dpi=200)
        plt.close()
        print(f"\n📈 Equity curve saved → outputs/charts/dashboard_equity_curve.png")

    print("\n" + "="*100)
    print("Refresh: python -m dashboard.portfolio_dashboard")
    print("="*100)

if __name__ == "__main__":
    show_dashboard()