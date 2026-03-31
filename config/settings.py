import os
from datetime import time
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Data Source
DATA_SOURCE = "yfinance"

# Watchlists
EQUITY_WATCHLIST = "config/equity_watchlist.txt"
CRYPTO_WATCHLIST = "config/crypto_watchlist.txt"

# Timeframes
TIMEFRAMES = {
    "equity": "1h",      # 15m, 1h, 1d etc.
    "crypto": "15m"
}

# Trading Hours (Eastern Time)
EQUITY_MARKET_OPEN = time(9, 30)
EQUITY_MARKET_CLOSE = time(16, 0)

# Risk & Portfolio
DEFAULT_RISK_PER_TRADE = 0.01   # 1% of capital per trade
MAX_POSITIONS_EQUITY = 5
MAX_POSITIONS_CRYPTO = 8
