import time
import schedule
from datetime import datetime
import pytz
from utils.data_fetcher import fetch_data, load_watchlist
from research.backtest_engine import run_backtest
from config.settings import EQUITY_WATCHLIST, TIMEFRAMES, EQUITY_MARKET_OPEN, EQUITY_MARKET_CLOSE


def is_market_open():
    now = datetime.now(pytz.timezone('US/Eastern'))
    current_time = now.time()
    return EQUITY_MARKET_OPEN <= current_time <= EQUITY_MARKET_CLOSE and now.weekday() < 5


def run_equity_bot():
    if not is_market_open():
        print(f"🌙 Market closed - Equity bot sleeping... ({time.strftime('%H:%M')})")
        return

    print(f"📈 Equity Bot Running - {time.strftime('%Y-%m-%d %H:%M:%S')}")
    tickers = load_watchlist(EQUITY_WATCHLIST)

    for ticker in tickers:
        data = fetch_data(ticker, period="30d", interval=TIMEFRAMES["equity"])
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
    schedule.every(15).minutes.do(run_equity_bot)

    while True:
        schedule.run_pending()
        time.sleep(60)