import pandas as pd
import numpy as np
import pandas_ta_classic as ta

def generate_signal(data: pd.DataFrame, strategy_name="ma_momentum"):
    """
    Generate trading signal + required indicators.
    Using pandas-ta-classic (Python 3.10 compatible)
    """
    try:
        df = data.copy()

        # === NORMALIZE COLUMNS ===
        df.columns = [col.lower() for col in df.columns]

        if len(df) < 50:
            print(f"⚠️ Not enough bars for signal ({len(df)})")
            return {"signal": 0, "strength": 0.0, "atr": 2.0, "rsi": 50.0}

        # === CALCULATE INDICATORS ===
        # ATR
        df['atr'] = ta.atr(high=df['high'], low=df['low'], close=df['close'], length=14)

        # RSI
        df['rsi'] = ta.rsi(close=df['close'], length=14)

        # Moving Averages
        df['sma_fast'] = ta.sma(close=df['close'], length=9)
        df['sma_slow'] = ta.sma(close=df['close'], length=21)

        # Fill NaNs
        df = df.ffill().bfill()

        latest = df.iloc[-1]

        # Default neutral
        signal = 0
        strength = 0.0

        if strategy_name == "ma_momentum":
            if (latest['sma_fast'] > latest['sma_slow'] and
                latest['close'] > latest['sma_fast']):
                signal = 1
                strength = (latest['close'] / latest['sma_slow'] - 1) * 100
            elif (latest['sma_fast'] < latest['sma_slow'] and
                  latest['close'] < latest['sma_fast']):
                signal = -1
                strength = (latest['sma_slow'] / latest['close'] - 1) * 100

        return {
            "signal": int(signal),
            "strength": float(strength),
            "atr": float(latest['atr']),
            "rsi": float(latest['rsi'])
        }

    except Exception as e:
        print(f"❌ generate_signal failed: {e}")
        import traceback
        traceback.print_exc()
        # Safe fallback
        return {
            "signal": 0,
            "strength": 0.0,
            "atr": 2.0,
            "rsi": 50.0
        }