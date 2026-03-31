import time
import schedule
from utils.data_fetcher import fetch_data, load_watchlist
from research.backtest_engine import run_backtest
from config.settings import CRYPTO_WATCHLIST, TIMEFRAMES


def run_crypto_bot():
    print(f"🚀 Crypto Bot Running - {time.strftime('%Y-%m-%d %H:%M:%S')}")
    tickers = load_watchlist(CRYPTO_WATCHLIST)

    for ticker in tickers:
        data = fetch_data(ticker, period="60d", interval=TIMEFRAMES["crypto"])
        if len(data) < 50:
            continue

        print(f"   Checking {ticker}...", end=" ")
        _, summary = run_backtest(
            data,
            strategy="ma_crossover",
            params={"short": 9, "long": 21}
        )

        latest_signal = summary.get("signal", 0) if "signal" in summary else 0
        signal_text = "BUY" if latest_signal == 1 else "SELL" if latest_signal == -1 else "HOLD"
        print(f"→ {signal_text}")


if __name__ == "__main__":
    schedule.every(15).minutes.do(run_crypto_bot)

    while True:
        schedule.run_pending()
        time.sleep(60)