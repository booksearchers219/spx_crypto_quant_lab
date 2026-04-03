import time
import schedule
import json
import os
import pandas as pd
import matplotlib

matplotlib.use('Agg')
from datetime import datetime
import pytz

from utils.data_fetcher import fetch_data, load_watchlist
from research.research_runner import run_research
from research.backtest_engine import run_backtest
from risk.risk_manager import RiskManager
from config.settings import EQUITY_WATCHLIST, TIMEFRAMES, EQUITY_MARKET_OPEN, EQUITY_MARKET_CLOSE
from utils.equity_logger import log_portfolio


# ================== AGGRESSIVENESS TUNING (Equity) ==================
risk_manager = RiskManager(capital=30000, name="equity")

BASE_FRACTION = 0.13      # Same as crypto for consistency
# ===================================================================


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


def run_equity_cycle():
    if not is_market_open():
        print(f"🌙 Market closed - Equity bot sleeping... ({time.strftime('%H:%M')})")
        return

    print(f"\n📈 Equity Bot Cycle - {time.strftime('%Y-%m-%d %H:%M:%S')} (Aggressive Mode)")

    active_tickers = load_best_equity_tickers()
    print(f"Using {len(active_tickers)} equity tickers: {active_tickers[:8]}")

    current_prices = {}

    for ticker in active_tickers[:8]:
        try:
            data = fetch_data(ticker, period="30d", interval=TIMEFRAMES["equity"])
            if data is None or len(data) < 100:
                continue

            current_price = float(data['Close'].iloc[-1].item())
            current_prices[ticker] = current_price

            df, summary = run_backtest(
                data,
                strategy="ma_slow",
                params={"short": 20, "long": 50},
                ticker=ticker
            )

            signal = int(df['signal'].iloc[-1]) if 'signal' in df.columns else 0

            # === Trailing stop check (if we have the method) ===
            if ticker in risk_manager.positions and hasattr(risk_manager, 'check_trailing_stop'):
                risk_manager.check_trailing_stop(ticker, current_price)

            # Buy
            if signal == 1 and ticker not in risk_manager.positions:
                success = risk_manager.open_position(
                    ticker,
                    current_price,
                    base_fraction=BASE_FRACTION
                )
                if success:
                    print(f"   ✅ BUY on {ticker} | Signal: {signal}")

            # Sell
            elif signal == -1 and ticker in risk_manager.positions:
                risk_manager.close_position(ticker, current_price, reason="ma_signal")

        except Exception as e:
            print(f"⚠️ Error processing {ticker}: {type(e).__name__} - {e}")
            continue

    total_value = risk_manager.get_current_value(current_prices)

    print(f"💰 Equity Portfolio Summary")
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


if __name__ == "__main__":
    print("📈 Starting Equity Bot (Aggressive Mode)...")
    schedule.every(6).hours.do(lambda: run_research(mode="equity"))

    run_equity_cycle()
    schedule.every(30).minutes.do(run_equity_cycle)

    while True:
        schedule.run_pending()
        time.sleep(60)