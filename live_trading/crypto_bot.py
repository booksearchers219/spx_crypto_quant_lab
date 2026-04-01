import time
import schedule
import json
import os
import matplotlib

matplotlib.use('Agg')

from utils.data_fetcher import fetch_data, load_watchlist
from research.research_runner import run_research
from research.backtest_engine import run_backtest
from risk.risk_manager import RiskManager
from config.settings import CRYPTO_WATCHLIST, TIMEFRAMES

risk_manager = RiskManager(capital=30000)


def load_best_crypto_tickers():
    """Smart loading: use recent research if available (less than 6 hours old)"""
    research_file = "outputs/latest_best.json"

    if os.path.exists(research_file):
        try:
            file_age_hours = (time.time() - os.path.getmtime(research_file)) / 3600
            with open(research_file, "r") as f:
                data = json.load(f)

            if data.get("mode") == "crypto" and file_age_hours < 6:
                print(f"📋 Using recent crypto research ({file_age_hours:.1f}h old)")
                return data.get("top_tickers", [])
            else:
                print(f"📋 Research is {file_age_hours:.1f}h old → Running fresh research")
        except Exception as e:
            print(f"⚠️ Error reading research file: {e}")

    print("🔬 Running fresh crypto research...")
    run_research(mode="crypto")

    try:
        with open(research_file, "r") as f:
            data = json.load(f)
            return data.get("top_tickers", [])
    except:
        print("⚠️ Failed to load research, falling back to watchlist")
        return load_watchlist(CRYPTO_WATCHLIST)


def run_crypto_cycle():
    print(f"\n🚀 Crypto Bot Cycle - {time.strftime('%Y-%m-%d %H:%M:%S')}")

    active_tickers = load_best_crypto_tickers()
    print(f"Using {len(active_tickers)} crypto tickers: {active_tickers[:6]}")

    current_prices = {}
    for ticker in active_tickers[:8]:
        data = fetch_data(ticker, period="60d", interval=TIMEFRAMES["crypto"])
        if len(data) < 100:
            continue

        current_price = data['Close'].iloc[-1]
        current_prices[ticker] = current_price

        df, summary = run_backtest(
            data,
            strategy="ma_slow",
            params={"short": 20, "long": 50},  # Slower = longer holds
            ticker=ticker
        )

        signal = df['signal'].iloc[-1] if 'signal' in df.columns else 0

        if signal == 1 and ticker not in risk_manager.positions:
            risk_manager.open_position(ticker, current_price)
        elif signal == -1 and ticker in risk_manager.positions:
            risk_manager.close_position(ticker, current_price)

    total_value = risk_manager.get_current_value(current_prices)
    print(
        f"💰 Crypto Portfolio → Cash: ${risk_manager.cash:,.2f} | Total: ${total_value:,.2f} | Positions: {len(risk_manager.positions)}")


if __name__ == "__main__":
    print("🚀 Starting Crypto Bot (Crypto-only tickers with smart research)...")
    schedule.every(6).hours.do(lambda: run_research(mode="crypto"))  # Less frequent

    run_crypto_cycle()
    schedule.every(15).minutes.do(run_crypto_cycle)

    while True:
        schedule.run_pending()
        time.sleep(60)