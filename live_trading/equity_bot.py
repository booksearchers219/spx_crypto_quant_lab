import time
import schedule
import json
import os
import matplotlib

matplotlib.use('Agg')
from datetime import datetime
import pytz

from utils.data_fetcher import fetch_data, load_watchlist
from research.research_runner import run_research
from research.backtest_engine import run_backtest
from risk.risk_manager import RiskManager
from config.settings import EQUITY_WATCHLIST, TIMEFRAMES, EQUITY_MARKET_OPEN, EQUITY_MARKET_CLOSE

risk_manager = RiskManager(capital=30000, name="equity")


def load_best_equity_tickers():
    research_file = "outputs/latest_best.json"

    if os.path.exists(research_file):
        try:
            file_age_hours = (time.time() - os.path.getmtime(research_file)) / 3600
            with open(research_file, "r") as f:
                data = json.load(f)

            if data.get("mode") == "equity" and file_age_hours < 6:
                print(f"📋 Using recent equity research ({file_age_hours:.1f}h old)")
                return data.get("top_tickers", [])
        except Exception as e:
            print(f"⚠️ Error reading research file: {e}")

    print("🔬 Running fresh equity research...")
    run_research(mode="equity")

    try:
        with open(research_file, "r") as f:
            data = json.load(f)
            return data.get("top_tickers", [])
    except:
        print("⚠️ Failed to load research, falling back to watchlist")
        return load_watchlist(EQUITY_WATCHLIST)


def is_market_open():
    now = datetime.now(pytz.timezone('US/Eastern'))
    return EQUITY_MARKET_OPEN <= now.time() <= EQUITY_MARKET_CLOSE and now.weekday() < 5


def run_equity_cycle():
    if not is_market_open():
        print(f"🌙 Market closed - Equity bot sleeping... ({time.strftime('%H:%M')})")
        return

    print(f"\n📈 Equity Bot Cycle - {time.strftime('%Y-%m-%d %H:%M:%S')}")

    active_tickers = load_best_equity_tickers()
    print(f"Using {len(active_tickers)} equity tickers: {active_tickers[:6]}")

    current_prices = {}
    for ticker in active_tickers[:8]:
        data = fetch_data(ticker, period="30d", interval=TIMEFRAMES["equity"])
        if len(data) < 100:
            continue

        current_price = data['Close'].iloc[-1]
        current_prices[ticker] = current_price

        df, summary = run_backtest(
            data,
            strategy="ma_slow",
            params={"short": 20, "long": 50},
            ticker=ticker
        )

        signal = df['signal'].iloc[-1] if 'signal' in df.columns else 0

        if signal == 1 and ticker not in risk_manager.positions:
            risk_manager.open_position(ticker, current_price)
        elif signal == -1 and ticker in risk_manager.positions:
            risk_manager.close_position(ticker, current_price)

    total_value = risk_manager.get_current_value(current_prices)

    from utils.equity_logger import log_portfolio

    # Log for graphing
    log_portfolio(
        bot_name="Crypto" if "crypto" in __file__ else "Equity",
        cash=risk_manager.cash,
        total_value=total_value,
        positions_count=len(risk_manager.positions),
        unrealized_pnl=total_value - risk_manager.initial_capital
    )

    print(f"💰 Equity Portfolio Summary")
    print(f"   Cash        : ${risk_manager.cash:,.2f}")
    print(f"   Total Value : ${total_value:,.2f}")
    print(f"   Positions   : {len(risk_manager.positions)}")

    if risk_manager.positions:
        print("   Open Positions:")
        for ticker, pos in risk_manager.positions.items():
            current_p = current_prices.get(ticker, pos['entry_price'])
            current_p = float(current_p.iloc[0]) if hasattr(current_p, 'iloc') else float(current_p)
            unrealized = (current_p - pos['entry_price']) * pos['quantity']
            print(
                f"     {ticker:8} | Qty: {pos['quantity']:>10.6f} | Entry: ${pos['entry_price']:.4f} | Current: ${current_p:.4f} | Unrealized: ${unrealized:,.2f}")

    print(
        f"   Combined P&L: ${total_value - risk_manager.initial_capital:,.2f} ({(total_value - risk_manager.initial_capital) / risk_manager.initial_capital * 100:+.2f}%)")
    print("-" * 90)


if __name__ == "__main__":
    print("📈 Starting Equity Bot (Equity-only tickers with smart research)...")
    schedule.every(6).hours.do(lambda: run_research(mode="equity"))

    run_equity_cycle()
    schedule.every(30).minutes.do(run_equity_cycle)

    while True:
        schedule.run_pending()
        time.sleep(60)