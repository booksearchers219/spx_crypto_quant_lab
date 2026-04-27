import time
import schedule
import os
import pandas as pd
import numpy as np
import matplotlib
import argparse
import logging
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo

matplotlib.use('Agg')

from utils.data_fetcher import fetch_data, load_watchlist
from research.research_runner import run_research
from research.backtest_engine import run_backtest
from risk.risk_manager import RiskManager
from config.settings import EQUITY_WATCHLIST
from strategies.strategy_engine import generate_signal
from utils.equity_logger import log_portfolio


def is_market_open():
    now = datetime.now(ZoneInfo("America/New_York"))
    if now.weekday() >= 5:
        return False
    current_time = now.time()
    return dt_time(9, 30) <= current_time < dt_time(16, 0)


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


def robust_fetch_data(ticker, period="60d", interval="1h", max_retries=5):
    for attempt in range(max_retries):
        try:
            data = fetch_data(ticker, period=period, interval=interval)
            if data is None or len(data) < 80:
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                return None
            print(f"✅ Fetched {len(data)} {interval} bars for {ticker} | Latest: {data.index[-1]}")
            return data
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(4)
            else:
                print(f"❌ Failed fetching {ticker}: {e}")
                return None


def run_equity_cycle(reset=False):
    logger = setup_logging("Equity")
    logger.info(f"🚀 Equity Bot Cycle - {time.strftime('%Y-%m-%d %H:%M:%S')}")

    market_open = is_market_open()
    print(f"{'✅ Market OPEN' if market_open else '🌙 Market CLOSED'} - {'Trading enabled' if market_open else 'Price update only'}")

    risk_manager = RiskManager(capital=80000, name="equity")
    if reset:
        risk_manager.reset()

    active_tickers = load_watchlist(EQUITY_WATCHLIST)
    if not market_open or datetime.now(ZoneInfo("America/New_York")).hour < 10:
        active_tickers = active_tickers[:20]

    logger.info(f"Using {len(active_tickers)} equity tickers")

    current_prices = {}

    for ticker in active_tickers:
        try:
            data = robust_fetch_data(ticker)
            if data is None or len(data) < 100:
                continue

            current_price = float(data['Close'].iloc[-1])
            current_prices[ticker] = current_price

            # Only run signals & trading when market is open
            if market_open:
                signal_info = generate_signal(data, strategy_name="ma_momentum")
                signal = signal_info["signal"]
                strength = signal_info["strength"]
                atr = signal_info["atr"]
                rsi = signal_info["rsi"]

                print(f"DEBUG {ticker:6} | sig:{signal} | RSI:{rsi:.1f} | ATR:{atr:.2f} | Price:{current_price:.2f} | Str:{strength:.2f}")

                # Check stops
                if ticker in risk_manager.positions:
                    risk_manager.check_trailing_stop(ticker, current_price)

                # BUY
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

                # SELL
                elif signal == -1 and ticker in risk_manager.positions:
                    risk_manager.close_position(ticker, current_price, reason="ma_momentum_signal")

        except Exception as e:
            print(f"⚠️ Error processing {ticker}: {e}")
            continue

    # Summary
    total_value = risk_manager.get_current_value(current_prices)
    pnl = total_value - risk_manager.initial_capital
    status = "OPEN" if market_open else "CLOSED"

    print(f"\n💰 Equity Portfolio Summary ({status})")
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
            print(f"   {ticker:6} | Qty: {pos['quantity']:>8.2f} | Entry: ${pos['entry_price']:.2f} | "
                  f"Current: ${curr_p:.2f} | Unrealized: ${unrealized:,.2f}")

    print("-" * 90)

    # Updated logging with reset support
    log_portfolio(
        "Equity_Bot",
        risk_manager.cash,
        total_value,
        len(risk_manager.positions),
        reset=reset
    )

    logger.info(f"Summary | Cash: ${risk_manager.cash:,.2f} | Total: ${total_value:,.2f} | Positions: {len(risk_manager.positions)}")
    risk_manager.save_state()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--reset', action='store_true')
    args = parser.parse_args()

    print("🚀 Starting Equity Bot (Improved Risk + Momentum Strategy)")

    run_equity_cycle(reset=args.reset)
    schedule.every(20).minutes.do(lambda: run_equity_cycle(reset=False))

    while True:
        schedule.run_pending()
        time.sleep(60)