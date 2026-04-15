import yfinance as yf
import pandas as pd
import time
import logging

logger = logging.getLogger(__name__)


def load_watchlist(file_path: str):
    """Load tickers from watchlist file"""
    try:
        with open(file_path, 'r') as f:
            tickers = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return tickers
    except Exception as e:
        logger.error(f"Failed to load watchlist {file_path}: {e}")
        return []


def fetch_data(ticker: str, period: str = "730d", interval: str = "1h", max_retries: int = 5) -> pd.DataFrame:
    """Improved fetch with better yfinance handling"""

    # Adjust period based on interval
    if interval in ["1m", "2m", "5m", "15m"]:
        period = "60d"
    elif interval in ["30m", "1h"]:
        period = "730d"
    else:
        period = "max"

    for attempt in range(max_retries):
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(
                period=period,
                interval=interval,
                auto_adjust=True,
                prepost=True,
                timeout=20
            )

            if data is None or data.empty or len(data) < 20:
                print(f"⚠️ No/empty data for {ticker} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt + 2)
                    continue
                return pd.DataFrame()

            # Keep only needed columns
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            data = data[[col for col in required_cols if col in data.columns]].copy()

            if len(data) < 20:
                print(f"⚠️ Too few bars for {ticker} ({len(data)})")
                return pd.DataFrame()

            data.index = pd.to_datetime(data.index)
            data = data.sort_index()

            print(f"✅ Fetched {len(data)} {interval} bars for {ticker} | Latest: {data.index[-1]}")
            return data

        except Exception as e:
            error_str = str(e).lower()
            if "nonetype" in error_str or "timeout" in error_str or "rate limit" in error_str:
                print(f"⚠️ yfinance NoneType / timeout for {ticker} (attempt {attempt + 1}/{max_retries})")
            else:
                print(f"⚠️ Error fetching {ticker} (attempt {attempt + 1}): {type(e).__name__}")

            if attempt < max_retries - 1:
                time.sleep(3 + attempt * 3)  # progressive backoff

    print(f"❌ Failed to fetch {ticker} after {max_retries} attempts")
    return pd.DataFrame()


def fetch_all_watchlist(watchlist_file: str, interval: str = "1h"):
    """Fetch data for all tickers"""
    tickers = load_watchlist(watchlist_file)
    data_dict = {}
    print(f"📡 Fetching {len(tickers)} tickers...")

    for ticker in tickers:
        df = fetch_data(ticker, interval=interval)
        if not df.empty:
            data_dict[ticker] = df

    print(f"✅ Successfully fetched {len(data_dict)}/{len(tickers)} tickers")
    return data_dict