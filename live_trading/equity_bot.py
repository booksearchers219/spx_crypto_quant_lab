import time
import schedule
import json
import os
import pandas as pd
import matplotlib
import argparse
import logging
from datetime import datetime
import pytz

matplotlib.use('Agg')

from utils.data_fetcher import fetch_data, load_watchlist
from research.research_runner import run_research
from research.backtest_engine import run_backtest
from risk.risk_manager import RiskManager
from config.settings import EQUITY_WATCHLIST, TIMEFRAMES, EQUITY_MARKET_OPEN, EQUITY_MARKET_CLOSE
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


# ================== AGGRESSIVENESS TUNING (MORE AGGRESSIVE) ==================
BASE_FRACTION = 0.35  # ↑ Larger position sizes (22% of cash per trade)
WEAK_DD_THRESHOLD = -35  # ↓ Accepts riskier stocks with bigger drawdowns
MAX_POSITIONS = 6


# ===========================================================================


def load_best_equity_tickers():
    research_file = "outputs/latest_best.json"
    if os.path.exists(research_file):
        try:
            file_age_hours = (time.time() - os.path.getmtime(research_file)) / 3600
            with open(research_file, "r") as f:
                data = json.load(f)

            if data.get("mode") == "equity" and file_age_hours < 6:
                print(f"📋 Using recent equity research ({file_age_hours:.1f}h old)")
                return data.get("top_tickers", [])
        except Exception as e:
            print(f"⚠️ Error reading research file: {e}")

    print("🔬 Running fresh equity research...")
    run_research(mode="equity")

    try:
        with open(research_file, "r") as f:
            data = json.load(f)
            return data.get("top_tickers", [])
    except:
        print("⚠️ Failed to load research, falling back to watchlist")
        return load_watchlist(EQUITY_WATCHLIST)


def is_market_open():
    now = datetime.now(pytz.timezone('US/Eastern'))
    return EQUITY_MARKET_OPEN <= now.time() <= EQUITY_MARKET_CLOSE and now.weekday() < 5


def run_equity_cycle(reset=False):
    logger = logging.getLogger("Equity")

    if not is_market_open():
        logger.info("🌙 Market closed - Equity bot sleeping...")
        print(f"🌙 Market closed - Equity bot sleeping... ({time.strftime('%H:%M')})")
        return

    logger.info(f"📈 Equity Bot Cycle - {time.strftime('%Y-%m-%d %H:%M:%S')} (Aggressive Mode - 22% sizing)")

    # === FIXED: Explicit state handling ===
    risk_manager = RiskManager(capital=30000, name="equity")

    if reset:
        risk_manager.reset()
    else:
        loaded = risk_manager.load_state()
        if loaded:
            logger.info(f"✅ State loaded successfully - Cash: ${risk_manager.cash:,.2f}")
        else:
            logger.info("ℹ️ No saved state found - starting fresh with $30,000")

    # Debug current state
    print(f"DEBUG → Cash: ${risk_manager.cash:,.2f} | Open Positions: {len(risk_manager.positions)}")

    active_tickers = load_best_equity_tickers()
    logger.info(f"Using {len(active_tickers)} equity tickers: {active_tickers[:8]}")

    current_prices = {}

    for ticker in active_tickers[:15]:
        try:
            data = fetch_data(ticker, period="30d", interval=TIMEFRAMES["equity"])
            if data is None or len(data) < 100:
                continue

            current_price = float(data['Close'].iloc[-1].item())
            current_prices[ticker] = current_price

            df, summary = run_backtest(
                data, strategy="ma_slow", params={"short": 20, "long": 50}, ticker=ticker
            )

            signal = int(df['signal'].iloc[-1]) if 'signal' in df.columns else 0

            if ticker in risk_manager.positions and hasattr(risk_manager, 'check_trailing_stop'):
                risk_manager.check_trailing_stop(ticker, current_price)

            # Buy
            # Buy
            if (
                    signal == 1 and
                    ticker not in risk_manager.positions and
                    len(risk_manager.positions) < MAX_POSITIONS
            ):
                success = risk_manager.open_position(
                    ticker,
                    current_price,
                    base_fraction=BASE_FRACTION
                )

            # Force deployment if too much cash idle
            if (
                    len(risk_manager.positions) < MAX_POSITIONS and
                    risk_manager.cash > risk_manager.initial_capital * 0.30
            ):
                if ticker not in risk_manager.positions:
                    success = risk_manager.open_position(
                        ticker,
                        current_price,
                        base_fraction=BASE_FRACTION
                    )
                    if success:
                        print(f"   🔥 FORCE BUY on {ticker} (deployment mode)")

                if success:
                    print(f"   ✅ BUY on {ticker} | Signal: {signal}")
                    print(f"   DEBUG Cash after buy: ${risk_manager.cash:,.2f}")

            # Sell
            elif signal == -1 and ticker in risk_manager.positions:
                risk_manager.close_position(ticker, current_price, reason="ma_signal")

        except Exception as e:
            print(f"⚠️ Error processing {ticker}: {type(e).__name__} - {e}")
            continue

    total_value = risk_manager.get_current_value(current_prices)

    print(f"💰 Equity Portfolio Summary (Aggressive Mode)")
    print(f"   Cash        : ${risk_manager.cash:,.2f}")
    print(f"   Total Value : ${total_value:,.2f}")
    print(f"   Positions   : {len(risk_manager.positions)}")

    if risk_manager.positions:
        print("   Open Positions:")
        for ticker, pos in risk_manager.positions.items():
            curr_p = current_prices.get(ticker, pos.get('entry_price', 0))
            curr_p = float(curr_p.iloc[-1].item()) if hasattr(curr_p, 'iloc') else float(curr_p)
            unrealized = (curr_p - pos['entry_price']) * pos['quantity']
            peak = pos.get('peak_price', pos['entry_price'])
            print(f"     {ticker:8} | Qty: {pos['quantity']:>10.6f} | Entry: ${pos['entry_price']:.4f} | "
                  f"Peak: ${peak:.4f} | Current: ${curr_p:.4f} | Unrealized: ${unrealized:,.2f}")

    pnl = total_value - risk_manager.initial_capital
    print(f"   Combined P&L: ${pnl:,.2f} ({pnl / risk_manager.initial_capital * 100:+.2f}%)")
    print("-" * 90)

    log_portfolio(
        bot_name="Equity",
        cash=risk_manager.cash,
        total_value=total_value,
        positions_count=len(risk_manager.positions)
    )

    logger.info(
        f"Portfolio Summary | Cash: ${risk_manager.cash:,.2f} | Total Value: ${total_value:,.2f} | P&L: ${pnl:,.2f} | Positions: {len(risk_manager.positions)}")

    # Force save state at the end
    risk_manager.save_state()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--reset', action='store_true', help='Reset portfolio to $30,000 and clear all positions')
    args = parser.parse_args()

    logger = setup_logging("Equity")

    print("📈 Starting Equity Bot (Aggressive Mode - 22% sizing)...")
    if args.reset:
        print("🔄 RESET flag detected — starting with fresh $30,000")
        logger.info("🔄 RESET flag detected — starting with fresh $30,000")

    schedule.every(6).hours.do(lambda: run_research(mode="equity"))

    run_equity_cycle(reset=args.reset)
    schedule.every(30).minutes.do(lambda: run_equity_cycle(reset=False))

    while True:
        schedule.run_pending()
        time.sleep(60)
