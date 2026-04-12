import time
import schedule
import json
import os
import pandas as pd
import matplotlib
import argparse
import logging
from datetime import datetime

matplotlib.use('Agg')

from utils.data_fetcher import fetch_data, load_watchlist
from research.research_runner import run_research
from research.backtest_engine import run_backtest
from risk.risk_manager import RiskManager
from config.settings import CRYPTO_WATCHLIST, TIMEFRAMES
from utils.equity_logger import log_portfolio


# ====================== LOGGING SETUP ======================
def setup_logging(bot_name: str):
    os.makedirs("logs", exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    log_filename = f"logs/{bot_name.lower()}_{today}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[
            logging.FileHandler(log_filename, mode='a', encoding='utf-8'),
            logging.StreamHandler()
        ],
        force=True
    )
    logger = logging.getLogger(bot_name)
    logger.info(f"🚀 Logging initialized for {bot_name}")
    return logger


def robust_fetch_data(ticker, period="60d", interval="15m", max_retries=3):
    for attempt in range(max_retries):
        try:
            data = fetch_data(ticker, period=period, interval=interval)
            if data is None or len(data) < 100:
                if attempt < max_retries - 1:
                    print(f"⚠️ Empty data for {ticker}, retrying ({attempt + 1}/{max_retries})...")
                    time.sleep(3 + attempt * 2)
                    continue
                print(f"⚠️ No usable data for {ticker} after retries")
                return None
            print(f"✅ Fetched {len(data)} {interval} bars for {ticker} | Latest: {data.index[-1]}")
            return data
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠️ Fetch error {ticker} (attempt {attempt + 1}) - retrying...")
                time.sleep(3 + attempt * 2)
            else:
                print(f"❌ Failed fetching {ticker}: {e}")
                return None


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


# ================== AGGRESSIVENESS TUNING ==================
BASE_FRACTION = 0.23
BUY_BUFFER = 0.998  # Allow buying slightly below short MA
RSI_MAX = 85
WEAK_DD_THRESHOLD = -40
MAX_POSITIONS = 8


# ===========================================================


def load_best_crypto_tickers():
    research_file = "outputs/latest_best.json"
    if os.path.exists(research_file):
        try:
            file_age_hours = (time.time() - os.path.getmtime(research_file)) / 3600
            with open(research_file, "r") as f:
                data = json.load(f)
            if data.get("mode") == "crypto" and file_age_hours < 6:
                print(f"📋 Using recent crypto research ({file_age_hours:.1f}h old)")
                return data.get("top_tickers", [])
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


def run_crypto_cycle(reset=False):
    logger = logging.getLogger("Crypto")
    logger.info(
        f"🚀 Crypto Bot Cycle - {time.strftime('%Y-%m-%d %H:%M:%S')} (Aggressive Mode - {BASE_FRACTION * 100:.0f}% sizing + 9% trail)")

    risk_manager = RiskManager(capital=30000, name="crypto")
    if reset:
        risk_manager.reset()

    active_tickers = load_best_crypto_tickers()
    logger.info(f"Using {len(active_tickers)} crypto tickers: {active_tickers}")

    current_prices = {}

    for ticker in active_tickers[:20]:
        try:
            data = robust_fetch_data(ticker)
            if data is None or len(data) < 150:
                continue

            current_price = float(data['Close'].iloc[-1])
            current_prices[ticker] = current_price

            # === Run backtest for signal ===
            df, summary = run_backtest(
                data, strategy="ma_fast", params={"short": 8, "long": 21}, ticker=ticker
            )
            signal = int(df['signal'].iloc[-1]) if 'signal' in df.columns else 0

            # Additional indicators
            df = df.copy()
            df['ma200'] = df['Close'].rolling(window=200).mean()
            df['rsi'] = calculate_rsi(df['Close'], period=14)

            close_value = float(df['Close'].iloc[-1])
            short_ma_value = float(df['short_ma'].iloc[-1]) if 'short_ma' in df.columns and pd.notna(
                df['short_ma'].iloc[-1]) else None
            ma200_value = float(df['ma200'].iloc[-1]) if pd.notna(df['ma200'].iloc[-1]) else None
            rsi_value = float(df['rsi'].iloc[-1]) if 'rsi' in df.columns and pd.notna(df['rsi'].iloc[-1]) else 50.0

            long_bias = 1 if ma200_value is None or close_value > ma200_value else 0

            # === DEBUG (very helpful) ===
            short_ma_str = f"{short_ma_value:.4f}" if short_ma_value is not None else "N/A"
            print(f"DEBUG {ticker:8} | signal:{signal} | bias:{long_bias} | "
                  f"RSI:{rsi_value:.1f} | Price:{close_value:.4f} | ShortMA:{short_ma_str}")

            # Trailing stop check for existing positions
            if ticker in risk_manager.positions:
                risk_manager.check_trailing_stop(ticker, current_price)

            # === MAIN ENTRY LOGIC ===
            if (signal == 1 and
                    long_bias == 1 and
                    short_ma_value is not None and
                    close_value > short_ma_value * BUY_BUFFER and
                    rsi_value < RSI_MAX and
                    ticker not in risk_manager.positions and
                    len(risk_manager.positions) < MAX_POSITIONS):

                success = risk_manager.open_position(
                    ticker, current_price, base_fraction=BASE_FRACTION, max_addons=2
                )
                if success:
                    print(f"✅ BUY on {ticker} | RSI:{rsi_value:.1f} Signal:{signal}")

            # === FORCE DEPLOYMENT if too much cash is idle ===
            elif (len(risk_manager.positions) < MAX_POSITIONS and
                  risk_manager.cash > risk_manager.initial_capital * 0.30 and
                  signal == 1 and long_bias == 1):

                success = risk_manager.open_position(
                    ticker, current_price, base_fraction=BASE_FRACTION, max_addons=2
                )
                if success:
                    print(f"🔥 FORCE BUY (high cash) on {ticker}")

            # === EXIT ===
            elif signal == -1 and ticker in risk_manager.positions:
                risk_manager.close_position(ticker, current_price, reason="ma_signal")

        except Exception as e:
            print(f"⚠️ Error processing {ticker}: {type(e).__name__} - {e}")
            continue

    # === Portfolio Summary ===
    total_value = risk_manager.get_current_value(current_prices)
    print(f"\n💰 Crypto Portfolio Summary (Aggressive Mode)")
    print(f"   Cash : ${risk_manager.cash:,.2f}")
    print(f"   Total Value : ${total_value:,.2f}")
    print(f"   Positions : {len(risk_manager.positions)}")
    print(f"   Combined P&L: ${total_value - risk_manager.initial_capital:,.2f} "
          f"({(total_value - risk_manager.initial_capital) / risk_manager.initial_capital * 100:+.2f}%)")
    print("-" * 90)

    log_portfolio(
        bot_name="Crypto_Aggressive_v1",
        cash=risk_manager.cash,
        total_value=total_value,
        positions_count=len(risk_manager.positions)
    )

    logger.info(f"Portfolio Summary | Cash: ${risk_manager.cash:,.2f} | "
                f"Total Value: ${total_value:,.2f} | P&L: ${total_value - risk_manager.initial_capital:,.2f} | "
                f"Positions: {len(risk_manager.positions)}")

    risk_manager.save_state()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--reset', action='store_true', help='Reset portfolio to $30,000 and clear all positions')
    args = parser.parse_args()

    logger = setup_logging("Crypto")
    print("🚀 Starting Crypto Bot (Aggressive Mode)")

    if args.reset:
        print("🔄 RESET flag detected — starting with fresh $30,000")

    schedule.every(6).hours.do(lambda: run_research(mode="crypto"))

    run_crypto_cycle(reset=args.reset)
    schedule.every(15).minutes.do(lambda: run_crypto_cycle(reset=False))

    while True:
        schedule.run_pending()
        time.sleep(60)