import os
import pandas as pd
import json
import argparse
from datetime import datetime
from utils.data_fetcher import fetch_all_watchlist
from research.backtest_engine import run_backtest
from config.settings import EQUITY_WATCHLIST, CRYPTO_WATCHLIST, TIMEFRAMES


def run_research(mode: str = "equity"):
    """Run research and save best tickers for live bots"""
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
            print(f"⏭️  Skipping {ticker} - not enough data")
            continue

        print(f"Running backtest on {ticker}...")
        _, summary = run_backtest(
            data,
            strategy="ma_fast",
            params={"short": 5, "long": 13},
            ticker=ticker
        )
        results[ticker] = summary

    if results:
        summary_df = pd.DataFrame.from_dict(results, orient='index')
        summary_df = summary_df.sort_values("total_return_pct", ascending=False)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        os.makedirs("outputs/reports", exist_ok=True)

        summary_df.to_csv(f"outputs/reports/{timestamp}_research_summary.csv")
        summary_df.to_json(f"outputs/reports/{timestamp}_research_summary.json", indent=4)

        # Save best tickers for live bots
        best_tickers = summary_df.head(8).index.tolist()
        best_data = {
            "mode": mode,
            "timestamp": timestamp,
            "top_tickers": best_tickers,
            "total_tickers_tested": len(results)
        }
        with open("outputs/latest_best.json", "w") as f:
            json.dump(best_data, f, indent=4)

        print(f"\n✅ Research Complete!")
        print(summary_df.head(10))
        print(f"\n📌 Best {len(best_tickers)} tickers saved to outputs/latest_best.json")
    else:
        print("\n⚠️ No successful backtests.")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run research for equity or crypto")
    parser.add_argument("--research_mode", choices=["equity", "crypto"], default="equity",
                        help="Which market to research")
    args = parser.parse_args()

    run_research(mode=args.research_mode)