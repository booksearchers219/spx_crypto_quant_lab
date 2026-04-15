import time
import schedule
import os
import pandas as pd
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
from utils.equity_logger import log_portfolio


def is_market_open():
    """Return True only during regular US market hours (9:30-16:00 ET, weekdays)"""
    now = datetime.now(ZoneInfo("America/New_York"))
    if now.weekday() >= 5:  # Weekend
        return False
    current_time = now.time()
    return dt_time(9, 30) <= current_time < dt_time(16, 0)


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


def robust_fetch_data(ticker, period="60d", interval="1h", max_retries=5):
    for attempt in range(max_retries):
        try:
            data = fetch_data(ticker, period=period, interval=interval)

            if data is None or len(data) < 30:
                print(f"⚠️ Insufficient data for {ticker} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(3 + attempt * 2)
                    continue
                return None

            print(f"✅ Fetched {len(data)} {interval} bars for {ticker} | Latest: {data.index[-1]}")
            return data

        except Exception as e:
            print(f"⚠️ Exception fetching {ticker} (attempt {attempt + 1}): {type(e).__name__}")
            if attempt < max_retries - 1:
                time.sleep(4 + attempt * 2)

    print(f"❌ Failed to fetch {ticker} after {max_retries} attempts - skipping")
    return None


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def run_equity_cycle(reset=False):
    logger = setup_logging("Equity")
    logger.info(f"🚀 Equity Bot Cycle - {time.strftime('%Y-%m-%d %H:%M:%S')}")

    market_open = is_market_open()
    print(
        f"{'✅ Market OPEN - Running full cycle' if market_open else '🌙 Market CLOSED (After-hours) - Updating prices only'}")

    risk_manager = RiskManager(capital=30000, name="equity")
    if reset:
        risk_manager.reset()

    active_tickers = load_watchlist(EQUITY_WATCHLIST)

    # Limit number of tickers early morning or when market is closed to reduce spam
    if not market_open or datetime.now(ZoneInfo("America/New_York")).hour < 10:
        active_tickers = active_tickers[:25]
        print(f"   (Limited to top 25 tickers for faster run)")

    logger.info(f"Using {len(active_tickers)} equity tickers")

    current_prices = {}

    for ticker in active_tickers:
        try:
            data = robust_fetch_data(ticker)
            if data is None or len(data) < 80:
                continue

            current_price = float(data['Close'].iloc[-1])
            current_prices[ticker] = current_price

            # Only run trading logic when market is open
            if market_open:
                df, summary = run_backtest(data, strategy="ma_fast", params={"short": 8, "long": 21}, ticker=ticker)
                signal = int(df['signal'].iloc[-1]) if 'signal' in df.columns else 0

                df = df.copy()
                df['rsi'] = calculate_rsi(df['Close'])

                close_value = float(df['Close'].iloc[-1])
                short_ma_value = float(df['short_ma'].iloc[-1]) if 'short_ma' in df.columns and pd.notna(
                    df['short_ma'].iloc[-1]) else None
                rsi_value = float(df['rsi'].iloc[-1]) if 'rsi' in df.columns and pd.notna(df['rsi'].iloc[-1]) else 50.0

                short_ma_str = f"{short_ma_value:.4f}" if short_ma_value is not None else "N/A"
                print(
                    f"DEBUG {ticker:6} | sig:{signal} | RSI:{rsi_value:.1f} | Price:{close_value:.2f} | ShortMA:{short_ma_str}")

                if ticker in risk_manager.positions:
                    risk_manager.check_trailing_stop(ticker, current_price)

                # Rebalance / DCA
                if risk_manager.should_rebalance() and risk_manager.cash > 800:
                    if ticker in risk_manager.positions:
                        success = risk_manager.add_to_position(ticker, current_price, 1.15)
                        if success:
                            print(f"🔄 Rebalance DCA → {ticker}")

                # Normal Buy
                if (signal == 1 and short_ma_value is not None and
                        close_value > short_ma_value * 0.99 and rsi_value < 78 and
                        ticker not in risk_manager.positions and
                        len(risk_manager.positions) < risk_manager.max_positions):

                    signal_strength = 1.45 if rsi_value < 40 else 1.2 if rsi_value < 50 else 1.0
                    success = risk_manager.open_position(ticker, current_price, signal_strength)
                    if success:
                        print(f"✅ BUY {ticker} | RSI:{rsi_value:.1f}")

                # Sell
                elif signal == -1 and ticker in risk_manager.positions:
                    risk_manager.close_position(ticker, current_price, reason="ma_signal")

        except Exception as e:
            print(f"⚠️ Error processing {ticker}: {e}")
            continue

    # === Summary ===
    total_value = risk_manager.get_current_value(current_prices)
    pnl = total_value - risk_manager.initial_capital
    status = "OPEN" if market_open else "CLOSED (After-hours/Weekend)"

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
            print(f"   {ticker:6} | Qty: {pos['quantity']:>8.4f} | Entry: ${pos['entry_price']:.4f} | "
                  f"Current: ${curr_p:.2f} | Unrealized: ${unrealized:,.2f}")

    print("-" * 90)

    log_portfolio("Equity_Bot", risk_manager.cash, total_value, len(risk_manager.positions))
    logger.info(
        f"Summary | Cash: ${risk_manager.cash:,.2f} | Total: ${total_value:,.2f} | Positions: {len(risk_manager.positions)}")
    risk_manager.save_state()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--reset', action='store_true')
    args = parser.parse_args()

    print("🚀 Starting Equity Bot (Aggressive + Rebalance Mode with Market Hours Check)")

    run_equity_cycle(reset=args.reset)
    schedule.every(20).minutes.do(lambda: run_equity_cycle(reset=False))

    while True:
        schedule.run_pending()
        time.sleep(60)