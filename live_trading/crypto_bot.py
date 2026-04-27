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

from utils.data_fetcher import fetch_data, load_watchlist
from research.research_runner import run_research
from research.backtest_engine import run_backtest
from risk.risk_manager import RiskManager
from config.settings import CRYPTO_WATCHLIST
from strategies.strategy_engine import generate_signal


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


def load_best_crypto_tickers():
    """Your original research-based ticker selector"""
    research_file = "outputs/latest_best.json"
    if os.path.exists(research_file):
        try:
            file_age_hours = (time.time() - os.path.getmtime(research_file)) / 3600
            with open(research_file, "r") as f:
                data = json.load(f)
            if data.get("mode") == "crypto" and file_age_hours < 6:
                print(f"📋 Using recent crypto research ({file_age_hours:.1f}h old)")
                return data.get("top_tickers", [])
        except:
            pass
    print("🔬 Running fresh crypto research...")
    run_research(mode="crypto")
    try:
        with open(research_file, "r") as f:
            return json.load(f).get("top_tickers", [])
    except:
        return load_watchlist(CRYPTO_WATCHLIST)


def run_crypto_cycle(reset=False):
    logger = setup_logging("Crypto")
    logger.info(f"🚀 Crypto Bot Cycle - {time.strftime('%Y-%m-%d %H:%M:%S')}")

    risk_manager = RiskManager(capital=80000, name="crypto")
    if reset:
        risk_manager.reset()

    active_tickers = load_best_crypto_tickers()
    logger.info(f"Using {len(active_tickers)} crypto tickers")

    current_prices = {}

    for ticker in active_tickers[:15]:   # Limit for speed
        try:
            data = robust_fetch_data(ticker)
            if data is None or len(data) < 150:
                continue

            current_price = float(data['Close'].iloc[-1])
            current_prices[ticker] = current_price

            # === NEW SIGNAL + BACKTEST ===
            signal_info = generate_signal(data, strategy_name="ma_momentum")
            signal = signal_info["signal"]
            strength = signal_info["strength"]
            atr = signal_info["atr"]
            rsi = signal_info["rsi"]

            print(f"DEBUG {ticker:8} | sig:{signal} | RSI:{rsi:.1f} | ATR:{atr:.4f} | Price:{current_price:.4f} | Strength:{strength:.2f}")

            # Trailing / hard stop check
            if ticker in risk_manager.positions:
                risk_manager.check_trailing_stop(ticker, current_price)

            # === BUY LOGIC ===
            if (signal == 1 and
                ticker not in risk_manager.positions and
                len(risk_manager.positions) < risk_manager.max_positions):

                success = risk_manager.open_position(
                    ticker=ticker,
                    entry_price=current_price,
                    atr=atr,
                    signal_strength=strength
                )
                if success:
                    print(f"✅ BUY {ticker} | RSI:{rsi:.1f} | Strength:{strength:.2f}")

            # === SELL LOGIC ===
            elif signal == -1 and ticker in risk_manager.positions:
                risk_manager.close_position(ticker, current_price, reason="ma_momentum_signal")

        except Exception as e:
            print(f"⚠️ Error processing {ticker}: {e}")
            continue

    # === Portfolio Summary ===
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
            curr_p = float(curr_p) if not hasattr(curr_p, 'iloc') else float(curr_p.iloc[-1])
            unrealized = (curr_p - pos['entry_price']) * pos['quantity']
            print(f"   {ticker:8} | Qty: {pos['quantity']:>10.4f} | Entry: ${pos['entry_price']:.4f} | "
                  f"Current: ${curr_p:.4f} | Unrealized: ${unrealized:,.2f}")

    print("-" * 90)

    from utils.equity_logger import log_portfolio
    log_portfolio("Crypto_Bot", risk_manager.cash, total_value, len(risk_manager.positions))

    logger.info(f"Summary | Cash: ${risk_manager.cash:,.2f} | Total: ${total_value:,.2f} | Positions: {len(risk_manager.positions)}")
    risk_manager.save_state()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--reset', action='store_true')
    args = parser.parse_args()

    print("🚀 Starting Crypto Bot (Improved Risk + Momentum Strategy)")

    schedule.every(6).hours.do(lambda: run_research(mode="crypto"))

    run_crypto_cycle(reset=args.reset)
    schedule.every(15).minutes.do(lambda: run_crypto_cycle(reset=False))

    while True:
        schedule.run_pending()
        time.sleep(60)