import pandas as pd
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
import os
from datetime import datetime


def run_backtest(data: pd.DataFrame, strategy: str = "ma_slow",
                 params: dict = None, initial_capital=10000, ticker: str = None):
    if params is None:
        params = {}

    df = data.copy()
    ticker_name = ticker or "Unknown"

    # Safe slow MA crossover for longer holds
    short = params.get("short", 20)
    long = params.get("long", 50)

    df['short_ma'] = df['Close'].rolling(window=short).mean()
    df['long_ma'] = df['Close'].rolling(window=long).mean()

    # Drop NaNs safely
    df = df.dropna().copy()

    # Simple signal
    df['signal'] = 0
    df.loc[df['short_ma'] > df['long_ma'], 'signal'] = 1
    df.loc[df['short_ma'] < df['long_ma'], 'signal'] = -1

    # Performance
    df['returns'] = df['Close'].pct_change()
    df['strategy_returns'] = df['signal'].shift(1) * df['returns']
    df['equity'] = initial_capital * (1 + df['strategy_returns']).cumprod()

    # Save outputs
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = f"outputs/reports/{timestamp}_{strategy}_{ticker_name}"
    os.makedirs(output_dir, exist_ok=True)

    df.to_csv(f"{output_dir}/full_results.csv")

    summary = {
        "ticker": ticker_name,
        "strategy": strategy,
        "total_return_pct": float((df['equity'].iloc[-1] / initial_capital - 1) * 100),
        "max_drawdown_pct": float(((df['equity'] / df['equity'].cummax()) - 1).min() * 100),
        "num_trades": int(df['signal'].diff().abs().sum() / 2),
        "final_equity": float(df['equity'].iloc[-1]),
        "bars_processed": len(df)
    }

    with open(f"{output_dir}/summary.json", "w") as f:
        json.dump(summary, f, indent=4)

    plt.figure(figsize=(14, 8))
    plt.plot(df['equity'], label='Strategy Equity', linewidth=2)
    plt.title(f"Slow MA - {ticker_name} | Return: {summary['total_return_pct']:.2f}%")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"outputs/charts/{timestamp}_{ticker_name}.png", dpi=200)
    plt.close()

    print(f"   ✅ {ticker_name} → Return: {summary['total_return_pct']:.2f}% | DD: {summary['max_drawdown_pct']:.2f}%")
    return df, summary