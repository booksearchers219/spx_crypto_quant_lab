import time
import schedule
import json
import os
import pandas as pd
import numpy as np
import matplotlib
import argparse
import logging
from datetime import datetime

matplotlib.use('Agg')

from utils.data_fetcher import fetch_data
from research.research_runner import run_research
from risk.risk_manager import RiskManager
from strategies.strategy_engine import generate_signal
from utils.equity_logger import log_portfolio


# ====================== INDICATOR HELPERS ======================
def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=period).mean()
    return df


# ====================== LOGGING SETUP ======================
def setup_logging(bot_name: str):
    os.makedirs("logs", exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    log_filename = f"logs/{bot_name.lower()}_{today}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[logging.FileHandler(log_filename, mode='a', encoding='utf-8'),
                  logging.StreamHandler()],
        force=True
    )
    return logging.getLogger(bot_name)


def robust_fetch_data(ticker, period="60d", interval="15m", max_retries=3):
    for attempt in range(max_retries):
        try:
            data = fetch_data(ticker, period=period, interval=interval)
            if data is None or len(data) < 100:
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                return None
            print(f"✅ Fetched {len(data)} {interval} bars for {ticker} | Latest: {data.index[-1]}")
            return data
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(3)
            else:
                print(f"❌ Failed fetching {ticker}: {e}")
                return None


def load_best_crypto_tickers(force_research: bool = False):
    research_file = "research/best_crypto_tickers.json"

    if force_research or not os.path.exists(research_file):
        print("🔬 Forcing fresh crypto research...")
        run_research(mode="crypto")

    elif os.path.exists(research_file):
        age_hours = (time.time() - os.path.getmtime(research_file)) / 3600
        if age_hours > 6:
            print(f"📋 Research is {age_hours:.1f}h old → Running fresh research")
            run_research(mode="crypto")

    try:
        with open(research_file, 'r') as f:
            data = json.load(f)
        tickers = data.get("tickers", ["BTC-USD"])
        print(f"✅ Loaded {len(tickers)} crypto tickers from research")
        return tickers
    except Exception as e:
        print(f"⚠️ Could not load research file: {e}. Using defaults.")
        return ["BTC-USD", "ETH-USD", "SOL-USD"]


def run_crypto_cycle(reset=False):
    logger = setup_logging("Crypto")
    logger.info(f"🚀 Crypto Bot Cycle - {time.strftime('%Y-%m-%d %H:%M:%S')}")

    risk_manager = RiskManager(capital=80000, name="crypto")
    if reset:
        risk_manager.reset()

    active_tickers = load_best_crypto_tickers(force_research=True)
    logger.info(f"Using {len(active_tickers)} crypto tickers")

    current_prices = {}

    for ticker in active_tickers[:15]:
        try:
            data = robust_fetch_data(ticker)
            if data is None or len(data) < 150:
                continue

            # Add indicators
            data = add_rsi(data)
            data = add_atr(data)

            current_price = float(data['Close'].iloc[-1])
            current_prices[ticker] = current_price

            signal_info = generate_signal(data, strategy_name="ma_momentum")
            signal = signal_info.get("signal", 0)
            strength = signal_info.get("strength", 1.0)
            atr = signal_info.get("atr", data['ATR'].iloc[-1] if 'ATR' in data.columns else 0)
            rsi = signal_info.get("rsi", data['RSI'].iloc[-1] if 'RSI' in data.columns else 50)

            print(f"DEBUG {ticker:8} | sig:{signal} | RSI:{rsi:.1f} | ATR:{atr:.4f} | Price:{current_price:.4f} | Strength:{strength:.2f}")

            if ticker in risk_manager.positions:
                risk_manager.check_trailing_stop(ticker, current_price)

            if (signal == 1 and ticker not in risk_manager.positions and
                len(risk_manager.positions) < risk_manager.max_positions):
                success = risk_manager.open_position(
                    ticker=ticker,
                    entry_price=current_price,
                    atr=atr,
                    signal_strength=strength
                )
                if success:
                    print(f"✅ BUY {ticker} | RSI:{rsi:.1f} | Strength:{strength:.2f}")

            elif signal == -1 and ticker in risk_manager.positions:
                risk_manager.close_position(ticker, current_price, reason="ma_momentum_signal")

        except Exception as e:
            print(f"⚠️ Error processing {ticker}: {e}")
            continue

    # Portfolio Summary
    total_value = risk_manager.get_current_value(current_prices)
    pnl = total_value - risk_manager.initial_capital

    print(f"\n💰 Crypto Portfolio Summary")
    print(f"   Cash          : ${risk_manager.cash:,.2f}")
    print(f"   Total Value   : ${total_value:,.2f}")
    print(f"   Open Positions: {len(risk_manager.positions)}/{risk_manager.max_positions}")
    print(f"   Total P&L     : ${pnl:,.2f} ({pnl / risk_manager.initial_capital * 100:+.2f}%)")

    if risk_manager.positions:
        print("\n📍 Open Positions:")
        for ticker, pos in risk_manager.positions.items():
            curr_p = current_prices.get(ticker, pos['entry_price'])
            unrealized = (curr_p - pos['entry_price']) * pos['quantity']
            print(f"   {ticker} | Qty: {pos['quantity']:.4f} | Entry: ${pos['entry_price']:.2f} | "
                  f"Current: ${curr_p:.2f} | Unrealized: ${unrealized:,.2f}")

    print("-" * 90)

    log_portfolio("Crypto_Bot", risk_manager.cash, total_value, len(risk_manager.positions), reset=reset)
    logger.info(f"Summary | Cash: ${risk_manager.cash:,.2f} | Total: ${total_value:,.2f} | Positions: {len(risk_manager.positions)}")
    risk_manager.save_state()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--reset', action='store_true')
    args = parser.parse_args()

    print("🚀 Starting Crypto Bot (Improved Risk + Momentum Strategy)")

    run_crypto_cycle(reset=args.reset)

    schedule.every(15).minutes.do(lambda: run_crypto_cycle(reset=False))
    schedule.every(6).hours.do(lambda: run_research(mode="crypto"))

    while True:
        schedule.run_pending()
        time.sleep(60)