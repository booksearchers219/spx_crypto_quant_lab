import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
import os
import pandas as pd
from datetime import datetime
from risk.risk_manager import RiskManager
from utils.data_fetcher import fetch_data


def show_dashboard():
    print("\n" + "=" * 120)
    print(" " * 40 + "COMBINED VIRTUAL TRADING DASHBOARD")
    print("=" * 120)
    print(f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    total_initial = 60000.0
    total_value = 0.0
    total_pnl = 0.0

    # Crypto Bot
    try:
        rm_crypto = RiskManager(capital=30000, name="crypto")

        current_prices = {}
        for ticker in list(rm_crypto.positions.keys()):
            data = fetch_data(ticker, period="5d", interval="15m")
            if not data.empty:
                current_prices[ticker] = data['Close'].iloc[-1]

        value_crypto = rm_crypto.get_current_value(current_prices)
        pnl_crypto = value_crypto - rm_crypto.initial_capital

        print(f"💰 CRYPTO BOT")
        print(f"   Initial     : ${rm_crypto.initial_capital:,.2f}")
        print(f"   Cash        : ${rm_crypto.cash:,.2f}")
        print(
            f"   Value       : ${value_crypto:,.2f} | P&L: ${pnl_crypto:,.2f} ({pnl_crypto / rm_crypto.initial_capital * 100:+.2f}%)")
        print(f"   Positions   : {len(rm_crypto.positions)}")

        if rm_crypto.trade_history:
            trades = pd.DataFrame(rm_crypto.trade_history)
            closed = trades[trades['action'] == 'SELL']
            wins = len(closed[closed['pnl'] > 0])
            win_rate = (wins / len(closed) * 100) if len(closed) > 0 else 0
            print(f"   Win Rate    : {win_rate:.1f}% ({wins}/{len(closed)} closed)")
            print(f"   Total Trades: {len(trades)}")

        total_value += value_crypto
        total_pnl += pnl_crypto
    except Exception as e:
        print(f"💰 CRYPTO BOT → Error: {str(e)[:100]}")

    print("-" * 85)

    # Equity Bot
    try:
        rm_equity = RiskManager(capital=30000, name="equity")

        current_prices = {}
        for ticker in list(rm_equity.positions.keys()):
            data = fetch_data(ticker, period="5d", interval="1h")
            if not data.empty:
                current_prices[ticker] = data['Close'].iloc[-1]

        value_equity = rm_equity.get_current_value(current_prices)
        pnl_equity = value_equity - rm_equity.initial_capital

        print(f"📈 EQUITY BOT")
        print(f"   Initial     : ${rm_equity.initial_capital:,.2f}")
        print(f"   Cash        : ${rm_equity.cash:,.2f}")
        print(
            f"   Value       : ${value_equity:,.2f} | P&L: ${pnl_equity:,.2f} ({pnl_equity / rm_equity.initial_capital * 100:+.2f}%)")
        print(f"   Positions   : {len(rm_equity.positions)}")

        if rm_equity.trade_history:
            trades = pd.DataFrame(rm_equity.trade_history)
            closed = trades[trades['action'] == 'SELL']
            wins = len(closed[closed['pnl'] > 0])
            win_rate = (wins / len(closed) * 100) if len(closed) > 0 else 0
            print(f"   Win Rate    : {win_rate:.1f}%")
            print(f"   Total Trades: {len(trades)}")

        total_value += value_equity
        total_pnl += pnl_equity
    except Exception as e:
        print(f"📈 EQUITY BOT → Error: {str(e)[:100]}")

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

    print("\nRefresh: python -m main --mode dashboard")
    print("=" * 120)


if __name__ == "__main__":
    show_dashboard()