import time
import schedule
import json
import matplotlib

matplotlib.use('Agg')

from utils.data_fetcher import fetch_data, load_watchlist
from research.research_runner import run_research
from research.backtest_engine import run_backtest
from risk.risk_manager import RiskManager
from config.settings import CRYPTO_WATCHLIST, TIMEFRAMES

risk_manager = RiskManager(capital=30000)


def load_best_crypto_tickers():
    """Force load only crypto tickers"""
    try:
        with open("outputs/latest_best.json", "r") as f:
            data = json.load(f)
            if data.get("mode") == "crypto":
                return data.get("top_tickers", [])
            else:
                print("⚠️ Latest research was for equity → Running fresh crypto research")
    except:
        print("⚠️ No research file found → Running fresh crypto research")

    # Run fresh research for crypto
    run_research(mode="crypto")

    # Load again
    try:
        with open("outputs/latest_best.json", "r") as f:
            data = json.load(f)
            return data.get("top_tickers", [])
    except:
        return load_watchlist(CRYPTO_WATCHLIST)


def run_crypto_cycle():
    print(f"\n🚀 Crypto Bot Cycle - {time.strftime('%Y-%m-%d %H:%M:%S')}")

    active_tickers = load_best_crypto_tickers()
    print(f"Using {len(active_tickers)} crypto tickers from research: {active_tickers[:6]}")

    current_prices = {}
    for ticker in active_tickers[:8]:
        data = fetch_data(ticker, period="60d", interval=TIMEFRAMES["crypto"])
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
        f"💰 Crypto Portfolio → Cash: ${risk_manager.cash:,.2f} | Total: ${total_value:,.2f} | Positions: {len(risk_manager.positions)}")


if __name__ == "__main__":
    print("🚀 Starting Crypto Bot (Crypto-only tickers)...")
    schedule.every(4).hours.do(lambda: run_research(mode="crypto"))

    run_crypto_cycle()
    schedule.every(15).minutes.do(run_crypto_cycle)

    while True:
        schedule.run_pending()
        time.sleep(60)