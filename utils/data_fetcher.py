import yfinance as yf
import pandas as pd
from datetime import datetime


def load_watchlist(file_path: str):
    """Load tickers from watchlist file"""
    with open(file_path, 'r') as f:
        tickers = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return tickers


def fetch_data(ticker: str, period: str = "730d", interval: str = "1h") -> pd.DataFrame:
    """Fetch OHLCV data using yfinance with better error handling"""
    try:
        if interval in ["1m", "2m", "5m", "15m"]:
            period = "60d"
        elif interval in ["30m", "1h"]:
            period = "730d"
        else:
            period = "max"

        data = yf.download(
            ticker,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
            prepost=True
        )

        if data is None or data.empty:
            print(f"⚠️ No data returned for {ticker}")
            return pd.DataFrame()

        data = data[['Open', 'High', 'Low', 'Close', 'Volume']]
        data.index = pd.to_datetime(data.index)
        data = data.sort_index()

        print(f"✅ Fetched {len(data)} {interval} bars for {ticker} | Latest: {data.index[-1]}")
        return data
    except Exception as e:
        print(f"❌ Error fetching {ticker}: {e}")
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
    return data_dict