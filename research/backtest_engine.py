import numpy as np
import pandas as pd
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
import os


def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Add RSI indicator"""
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Add ATR indicator"""
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=period).mean()
    return df


def run_backtest(data: pd.DataFrame, strategy: str = "ma_momentum",
                 params: dict = None, initial_capital=10000, ticker: str = None):
    if params is None:
        params = {}

    df = data.copy()
    ticker_name = ticker or "Unknown"

    # Add indicators if missing
    if 'RSI' not in df.columns:
        df = add_rsi(df)
    if 'ATR' not in df.columns:
        df = add_atr(df)

    # Strategy signals
    from strategies.strategy_engine import generate_signal

    signals = []
    for i in range(50, len(df)):
        window = df.iloc[i - 100:i + 1] if i > 100 else df.iloc[:i + 1]
        sig = generate_signal(window, strategy_name=strategy, **params)
        signals.append(sig["signal"])

    # Pad signals
    signals = [0] * (len(df) - len(signals)) + signals
    df['signal'] = signals

    # Backtest calculations
    df['returns'] = df['Close'].pct_change()
    df['strategy_returns'] = df['signal'].shift(1) * df['returns']

    commission = 0.0010
    slippage = 0.0008
    df['strategy_returns'] = df['strategy_returns'] - (commission + slippage) * df['signal'].shift(1).abs()

    df['equity'] = initial_capital * (1 + df['strategy_returns'].fillna(0)).cumprod()

    df_clean = df.dropna(subset=['strategy_returns'])

    total_return = (df['equity'].iloc[-1] / initial_capital - 1) * 100
    max_dd = ((df['equity'] / df['equity'].cummax()) - 1).min() * 100

    returns = df_clean['strategy_returns']
    if len(returns) < 10 or returns.std() == 0:
        sharpe = 0.0
    else:
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252 * 96)

    # Save results
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    output_dir = f"outputs/reports/{timestamp}_{strategy}_{ticker_name}"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs("outputs/charts", exist_ok=True)

    df.to_csv(f"{output_dir}/full_results.csv")

    summary = {
        "ticker": ticker_name,
        "strategy": strategy,
        "total_return_pct": float(total_return),
        "max_drawdown_pct": float(max_dd),
        "sharpe_ratio": float(sharpe),
        "final_equity": float(df['equity'].iloc[-1]),
        "bars_processed": len(df),
        "trades": int(df['signal'].diff().abs().sum() / 2)
    }

    with open(f"{output_dir}/summary.json", "w") as f:
        json.dump(summary, f, indent=4)

    # Plot
    plt.figure(figsize=(14, 8))
    plt.plot(df['equity'], label='Strategy Equity', linewidth=2)
    plt.title(f"{ticker_name} | Return: {total_return:.1f}% | DD: {max_dd:.1f}% | Sharpe: {sharpe:.2f}")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(f"outputs/charts/{timestamp}_{ticker_name}.png", dpi=200)
    plt.close()

    print(f"   ✅ {ticker_name} → Return: {total_return:.1f}% | DD: {max_dd:.1f}% | Sharpe: {sharpe:.2f} | Trades: {summary['trades']}")
    return df, summary