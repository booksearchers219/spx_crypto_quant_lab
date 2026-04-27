import json
import os
import pandas as pd
from research.backtest_engine import run_backtest
from utils.data_fetcher import fetch_data


def run_research(mode="crypto"):
    print("🔬 Starting Research Mode:", mode.upper())

    if mode == "crypto":
        tickers = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", 
                   "ADA-USD", "DOGE-USD", "AVAX-USD", "LINK-USD", "DOT-USD",
                   "LTC-USD", "ATOM-USD", "NEAR-USD", "FIL-USD", "ETC-USD",
                   "XLM-USD", "ARB-USD"]

        print(f"📡 Fetching {len(tickers)} tickers...")

        results = []
        for ticker in tickers:
            try:
                data = fetch_data(ticker, period="60d", interval="15m")
                if data is None or len(data) < 100:
                    continue

                print(f"Running backtest on {ticker}...")
                _, summary = run_backtest(data, ticker=ticker)

                results.append({
                    "ticker": ticker,
                    "sharpe": summary.get("sharpe_ratio", 0),
                    "return": summary.get("total_return_pct", 0),
                    "trades": summary.get("trades", 0)
                })
            except Exception as e:
                print(f"   ⚠️ Backtest failed for {ticker}: {e}")

        # Save best tickers
        results.sort(key=lambda x: x["sharpe"], reverse=True)
        best_tickers = [r["ticker"] for r in results[:8]]

        os.makedirs("research", exist_ok=True)
        with open("research/best_crypto_tickers.json", "w") as f:
            json.dump({"tickers": best_tickers, "timestamp": str(pd.Timestamp.now())}, f, indent=2)

        print("✅ Research Complete!")
        print(f"📌 Best 8 tickers saved to research/best_crypto_tickers.json")
        
        # Also save to outputs for legacy
        os.makedirs("outputs", exist_ok=True)
        with open("outputs/latest_best.json", "w") as f:
            json.dump({"tickers": best_tickers}, f, indent=2)

        return best_tickers

    return []
