import time
import schedule
import json
import os
import pandas as pd
import matplotlib

matplotlib.use('Agg')

from utils.data_fetcher import fetch_data, load_watchlist
from research.research_runner import run_research
from research.backtest_engine import run_backtest
from risk.risk_manager import RiskManager
from config.settings import CRYPTO_WATCHLIST, TIMEFRAMES
from utils.equity_logger import log_portfolio


def robust_fetch_data(ticker, period="60d", interval="15m", max_retries=3):
    for attempt in range(max_retries):
        try:
            data = fetch_data(ticker, period=period, interval=interval)
            if data is None or len(data) < 50:
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
                print(f"⚠️ Fetch error {ticker} (attempt {attempt+1}) - retrying...")
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
risk_manager = RiskManager(capital=30000, name="crypto")

# Change these numbers to tune aggression:
BASE_FRACTION = 0.13      # was 0.07 → bigger positions
BUY_BUFFER = 1.000        # was 1.003 → easier entry
RSI_MAX = 73              # was 67 → allows hotter entries
TRAIL_PERCENT = 0.09      # was 0.07 → 9% trailing stop
WEAK_DD_THRESHOLD = -27   # was -22 → allows slightly riskier coins
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


def run_crypto_cycle():
    print(f"\n🚀 Crypto Bot Cycle - {time.strftime('%Y-%m-%d %H:%M:%S')} (Aggressive Mode - 13% sizing + 9% trail)")

    active_tickers = load_best_crypto_tickers()
    print(f"Using {len(active_tickers)} crypto tickers: {active_tickers}")

    current_prices = {}

    for ticker in active_tickers[:12]:
        try:
            data = robust_fetch_data(ticker)
            if data is None or len(data) < 150:
                print(f"⚠️ Insufficient data for {ticker}, skipping")
                continue

            current_price = float(data['Close'].iloc[-1].item())
            current_prices[ticker] = current_price

            df, summary = run_backtest(
                data, strategy="ma_fast", params={"short": 8, "long": 21}, ticker=ticker
            )

            # Weak ticker filter (slightly loosened)
            if isinstance(summary, dict):
                max_dd = summary.get('max_drawdown', 0)
                if max_dd < WEAK_DD_THRESHOLD:
                    print(f"   ⏭️ Skipping {ticker} - too weak (Max DD: {max_dd:.1f}%)")
                    continue

            signal = int(df['signal'].iloc[-1]) if 'signal' in df.columns else 0

            df = df.copy()
            df['ma200'] = df['Close'].rolling(window=200).mean()
            df['rsi'] = calculate_rsi(df['Close'], period=14)

            close_value = float(df['Close'].iloc[-1].item())
            ma200_value = float(df['ma200'].iloc[-1].item()) if pd.notna(df['ma200'].iloc[-1]) else None
            short_ma_value = float(df['short_ma'].iloc[-1].item()) if 'short_ma' in df.columns and pd.notna(df['short_ma'].iloc[-1]) else None
            rsi_value = float(df['rsi'].iloc[-1]) if 'rsi' in df.columns and pd.notna(df['rsi'].iloc[-1]) else 50.0

            long_bias = 1 if ma200_value is not None and close_value > ma200_value else 0

            buy_condition = (
                signal == 1 and
                long_bias == 1 and
                short_ma_value is not None and
                close_value > short_ma_value * BUY_BUFFER and
                rsi_value < RSI_MAX
            )

            # Trailing stop check
            if ticker in risk_manager.positions:
                risk_manager.check_trailing_stop(ticker, current_price)

            # Buy
            if buy_condition and ticker not in risk_manager.positions:
                success = risk_manager.open_position(ticker, current_price, base_fraction=BASE_FRACTION, max_addons=2)
                if success:
                    print(f"   ✅ BUY on {ticker} | Signal:{signal} Bias:{long_bias} RSI:{rsi_value:.1f}")

            # Sell on signal
            elif signal == -1 and ticker in risk_manager.positions:
                risk_manager.close_position(ticker, current_price, reason="ma_signal")

        except Exception as e:
            print(f"⚠️ Error processing {ticker}: {type(e).__name__} - {e}")
            continue

    # Portfolio Summary
    total_value = risk_manager.get_current_value(current_prices)

    print(f"\n💰 Crypto Portfolio Summary (Aggressive Mode)")
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
        bot_name="Crypto_Aggressive_v1",
        cash=risk_manager.cash,
        total_value=total_value,
        positions_count=len(risk_manager.positions)
    )


if __name__ == "__main__":
    print("🚀 Starting Crypto Bot (Aggressive Mode - tuned for more trades)...")
    schedule.every(6).hours.do(lambda: run_research(mode="crypto"))

    run_crypto_cycle()
    schedule.every(15).minutes.do(run_crypto_cycle)

    while True:
        schedule.run_pending()
        time.sleep(60)