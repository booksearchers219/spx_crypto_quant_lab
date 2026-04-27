import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
import os


def run_backtest(data: pd.DataFrame, strategy: str = "ma_momentum",
                 params: dict = None, initial_capital=10000, ticker: str = None):
    if params is None:
        params = {}

    df = data.copy()
    ticker_name = ticker or "Unknown"

    # Use new strategy engine
    from strategies.strategy_engine import generate_signal, calculate_atr

    # Run signals on historical data
    signals = []
    for i in range(50, len(df)):  # Warm-up period
        window = df.iloc[i - 100:i + 1] if i > 100 else df.iloc[:i + 1]
        sig = generate_signal(window, strategy_name=strategy, **params)
        signals.append(sig["signal"])

    # Pad beginning with zeros
    signals = [0] * (len(df) - len(signals)) + signals
    df['signal'] = signals

    # More realistic backtest
    df['returns'] = df['Close'].pct_change()
    df['strategy_returns'] = df['signal'].shift(1) * df['returns']

    # Add realistic costs
    commission = 0.0010  # 0.10%
    slippage = 0.0008   # 0.08%
    df['strategy_returns'] = df['strategy_returns'] - (commission + slippage) * df['signal'].shift(1).abs()

    # Drop NaN rows for metrics
    df_clean = df.dropna(subset=['strategy_returns'])

    # Performance metrics
    total_return = (df['equity'].iloc[-1] / initial_capital - 1) * 100 if 'equity' in df.columns else 0
    max_dd = ((df['equity'] / df['equity'].cummax()) - 1).min() * 100 if 'equity' in df.columns else 0

    # Improved Sharpe (15m bars → ~96 periods per day)
    returns = df_clean['strategy_returns']
    if len(returns) < 10 or returns.std() == 0:
        sharpe = 0.0
    else:
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252 * 96)

    # Calculate equity curve (after cleaning)
    df['equity'] = initial_capital * (1 + df['strategy_returns']).cumprod()

    # Save outputs
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
    plt.title(f"{ticker_name} | {strategy} | Return: {total_return:.1f}% | DD: {max_dd:.1f}% | Sharpe: {sharpe:.2f}")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(f"outputs/charts/{timestamp}_{ticker_name}.png", dpi=200)
    plt.close()

    print(f"   ✅ {ticker_name} → Return: {total_return:.1f}% | DD: {max_dd:.1f}% | Sharpe: {sharpe:.2f}")
    return df, summary