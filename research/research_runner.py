import os
import pandas as pd
from datetime import datetime
from utils.data_fetcher import fetch_all_watchlist
from research.backtest_engine import run_backtest
from config.settings import EQUITY_WATCHLIST, CRYPTO_WATCHLIST, TIMEFRAMES


def run_research(mode: str = "equity"):
    """Run backtests on entire watchlist"""
    print(f"\n🔬 Starting Research Mode: {mode.upper()}\n")

    if mode == "equity":
        watchlist_file = EQUITY_WATCHLIST
        interval = TIMEFRAMES["equity"]
    else:
        watchlist_file = CRYPTO_WATCHLIST
        interval = TIMEFRAMES["crypto"]

    data_dict = fetch_all_watchlist(watchlist_file, interval=interval)

    results = {}
    for ticker, data in data_dict.items():
        if len(data) < 100:
            print(f"⏭️  Skipping {ticker} - not enough data ({len(data)} bars)")
            continue

        print(f"Running backtest on {ticker}...")
        _, summary = run_backtest(
            data,
            strategy="ma_crossover",
            params={"short": 9, "long": 21},
            ticker=ticker
        )

        results[ticker] = summary

    # Save summary safely
    if results:
        summary_df = pd.DataFrame.from_dict(results, orient='index')
        summary_df = summary_df.sort_values("total_return_pct", ascending=False)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        os.makedirs("outputs/reports", exist_ok=True)

        summary_df.to_csv(f"outputs/reports/{timestamp}_research_summary.csv")
        summary_df.to_json(f"outputs/reports/{timestamp}_research_summary.json", indent=4)

        print(f"\n✅ Research Complete! Top performers:")
        print(summary_df.head(10))
    else:
        print("\n⚠️ No successful backtests. Check data fetching.")

    return results


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "equity"
    run_research(mode=mode)
