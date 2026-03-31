import pandas as pd

def generate_signal(data: pd.DataFrame, strategy_name: str = "ma_crossover", **kwargs):
    df = data.copy()
    
    if strategy_name == "ma_crossover":
        short = kwargs.get("short", 9)
        long = kwargs.get("long", 21)
        df['short_ma'] = df['Close'].rolling(short).mean()
        df['long_ma'] = df['Close'].rolling(long).mean()
        signal = 1 if df['short_ma'].iloc[-1] > df['long_ma'].iloc[-1] else -1 if df['short_ma'].iloc[-1] < df['long_ma'].iloc[-1] else 0
    
    elif strategy_name == "rsi":
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_val = rsi.iloc[-1]
        signal = 1 if rsi_val < 30 else -1 if rsi_val > 70 else 0
    
    else:
        signal = 0
    
    return {"signal": signal, "strategy": strategy_name}
