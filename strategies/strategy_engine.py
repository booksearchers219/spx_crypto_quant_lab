import pandas as pd
import numpy as np


def calculate_atr(data: pd.DataFrame, period: int = 14) -> float:
    """Calculate Average True Range for dynamic stops"""
    df = data.copy()
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean().iloc[-1]
    return float(atr) if not pd.isna(atr) else float(df['Close'].iloc[-1] * 0.02)


def generate_signal(data: pd.DataFrame, strategy_name: str = "ma_momentum", **kwargs):
    """
    Improved multi-factor signal generator
    Returns dict with signal, strength, and ATR for risk sizing
    """
    df = data.copy()
    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df.get('Volume', pd.Series([0] * len(df)))

    result = {
        "signal": 0,
        "strength": 1.0,
        "atr": calculate_atr(df),
        "rsi": 50.0,
        "strategy": strategy_name
    }

    if strategy_name == "ma_momentum":
        short = kwargs.get("short", 9)
        long = kwargs.get("long", 21)

        df['short_ma'] = close.rolling(short).mean()
        df['long_ma'] = close.rolling(long).mean()

        # Momentum
        df['momentum'] = close.pct_change(5)

        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_val = float(rsi.iloc[-1])

        last_short = float(df['short_ma'].iloc[-1])
        last_long = float(df['long_ma'].iloc[-1])
        last_mom = float(df['momentum'].iloc[-1])

        result["rsi"] = rsi_val

        if (last_short > last_long and
                last_mom > 0 and
                rsi_val < 68):  # Not extremely overbought
            result["signal"] = 1
            result["strength"] = 1.6 if rsi_val < 40 else 1.3 if rsi_val < 50 else 1.0

        elif (last_short < last_long and rsi_val > 32):
            result["signal"] = -1
            result["strength"] = 1.0

    elif strategy_name == "rsi":
        # Pure RSI fallback
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_val = float(rsi.iloc[-1])
        result["rsi"] = rsi_val

        if rsi_val < 32:
            result["signal"] = 1
            result["strength"] = 1.5
        elif rsi_val > 68:
            result["signal"] = -1

    return result