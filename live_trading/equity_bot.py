import time
import schedule
import json
import matplotlib

matplotlib.use('Agg')
from datetime import datetime
import pytz

from utils.data_fetcher import fetch_data, load_watchlist
from research.research_runner import run_research
from research.backtest_engine import run_backtest
from risk.risk_manager import RiskManager
from config.settings import EQUITY_WATCHLIST, TIMEFRAMES, EQUITY_MARKET_OPEN, EQUITY_MARKET_CLOSE

risk_manager = RiskManager(capital=30000)


def load_best_equity_tickers():
    """Force load only equity tickers"""
    try:
        with open("outputs/latest_best.json", "r") as f:
            data = json.load(f)
            if data.get("mode") == "equity":
                return data.get("top_tickers", [])
            else:
                print("⚠️ Latest research was for crypto → Running fresh equity research")
    except:
        print("⚠️ No research file found → Running fresh equity research")

    # Run fresh research for equity
    run_research(mode="equity")

    # Load again
    try:
        with open("outputs/latest_best.json", "r") as f:
            data = json.load(f)
            return data.get("top_tickers", [])
    except:
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
    print(f"Using {len(active_tickers)} equity tickers from research: {active_tickers[:6]}")

    current_prices = {}
    for ticker in active_tickers[:8]:
        data = fetch_data(ticker, period="30d", interval=TIMEFRAMES["equity"])
        if len(data) < 100:
            continue

        current_price = data['Close'].iloc[-1]
        current_prices[ticker] = current_price

        _, summary = run_backtest(
            data,
            strategy="ma_fast",
            params={"short": 3, "long": 8},
            ticker=ticker
        )

        signal = summary.get("signal", 0)

        if signal == 1 and ticker not in risk_manager.positions:
            risk_manager.open_position(ticker, current_price)
        elif signal == -1 and ticker in risk_manager.positions:
            risk_manager.close_position(ticker, current_price)

    total_value = risk_manager.get_current_value(current_prices)
    print(
        f"💰 Equity Portfolio → Cash: ${risk_manager.cash:,.2f} | Total: ${total_value:,.2f} | Positions: {len(risk_manager.positions)}")


if __name__ == "__main__":
    print("📈 Starting Equity Bot (Equity-only tickers)...")
    schedule.every(4).hours.do(lambda: run_research(mode="equity"))

    run_equity_cycle()
    schedule.every(30).minutes.do(run_equity_cycle)

    while True:
        schedule.run_pending()
        time.sleep(60)