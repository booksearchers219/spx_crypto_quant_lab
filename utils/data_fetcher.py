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


def fetch_data(ticker: str, period: str = "730d", interval: str = "1h", max_retries: int = 3) -> pd.DataFrame:
    """Fetch OHLCV data using yfinance with robust error handling"""

    # Adjust period based on interval
    if interval in ["1m", "2m", "5m", "15m"]:
        period = "60d"
    elif interval in ["30m", "1h"]:
        period = "730d"
    else:
        period = "max"

    for attempt in range(max_retries):
        try:
            # Try to import scipy early to catch missing dependency clearly
            try:
                import scipy
            except ImportError:
                print(f"❌ scipy is required by yfinance but not installed for {ticker}")
                print("   Run: pip install scipy")
                return pd.DataFrame()

            stock = yf.Ticker(ticker)
            data = stock.history(
                period=period,
                interval=interval,
                auto_adjust=True,
                prepost=True,
                # repair=True  # commented out for now - can trigger more issues
            )

            if data is None or data.empty:
                print(f"⚠️ No data returned for {ticker} (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt + 1)
                    continue
                return pd.DataFrame()

            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in data.columns for col in required_cols):
                print(f"⚠️ Missing columns for {ticker}")
                return pd.DataFrame()

            data = data[required_cols].copy()
            data.index = pd.to_datetime(data.index)
            data = data.sort_index()

            print(f"✅ Fetched {len(data)} {interval} bars for {ticker} | Latest: {data.index[-1]}")
            return data

        except Exception as e:
            error_msg = str(e).lower()
            if "nonetype" in error_msg or "subscriptable" in error_msg:
                print(f"⚠️ yfinance NoneType bug for {ticker} (attempt {attempt + 1}/{max_retries})")
            elif "scipy" in error_msg:
                print(f"❌ Missing scipy dependency for {ticker}")
                print("   Fix: pip install scipy")
                return pd.DataFrame()
            else:
                print(f"❌ Error fetching {ticker} (attempt {attempt + 1}): {type(e).__name__} - {e}")

            if attempt < max_retries - 1:
                time.sleep(2 ** attempt + 2)
            else:
                print(f"❌ Giving up on {ticker} after {max_retries} attempts")
                return pd.DataFrame()

    return pd.DataFrame()


def fetch_all_watchlist(watchlist_file: str, interval: str = "1h"):
    """Fetch data for all tickers in a watchlist"""
    tickers = load_watchlist(watchlist_file)
    data_dict = {}
    print(f"📡 Fetching {len(tickers)} tickers from {watchlist_file}...")

    for ticker in tickers:
        df = fetch_data(ticker, interval=interval)
        if not df.empty:
            data_dict[ticker] = df

    print(f"✅ Successfully fetched data for {len(data_dict)}/{len(tickers)} tickers")
    return data_dict