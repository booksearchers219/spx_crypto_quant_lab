import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os

def plot_equity_curve():
    log_file = "outputs/equity_log.csv"
    
    if not os.path.exists(log_file):
        print("❌ No equity_log.csv found yet. Run the bots for a while first.")
        return
    
    df = pd.read_csv(log_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    plt.figure(figsize=(14, 8))
    
    # Plot Crypto
    crypto = df[df['bot'] == 'Crypto']
    if not crypto.empty:
        plt.plot(crypto['timestamp'], crypto['total_value'], label='Crypto Bot', linewidth=2.5, marker='o', markersize=4)
    
    # Plot Equity
    equity = df[df['bot'] == 'Equity']
    if not equity.empty:
        plt.plot(equity['timestamp'], equity['total_value'], label='Equity Bot', linewidth=2.5, marker='s', markersize=4)
    
    # Plot Combined
    # Group by timestamp and sum
    combined = df.groupby('timestamp')['total_value'].sum().reset_index()
    plt.plot(combined['timestamp'], combined['total_value'], label='Combined (Crypto + Equity)', 
             linewidth=3, color='purple', linestyle='--')
    
    plt.title('Portfolio Equity Curve Over Time', fontsize=16, pad=20)
    plt.xlabel('Time')
    plt.ylabel('Portfolio Value ($)')
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=12)
    
    # Format x-axis
    plt.gcf().autofmt_xdate()
    
    # Add value labels on the last point
    if not crypto.empty:
        last_c = crypto.iloc[-1]
        plt.annotate(f'Crypto: ${last_c["total_value"]:,.0f}', 
                    xy=(last_c['timestamp'], last_c['total_value']),
                    xytext=(10, 10), textcoords='offset points')
    
    if not equity.empty:
        last_e = equity.iloc[-1]
        plt.annotate(f'Equity: ${last_e["total_value"]:,.0f}', 
                    xy=(last_e['timestamp'], last_e['total_value']),
                    xytext=(10, -15), textcoords='offset points')
    
    plt.tight_layout()
    plt.savefig("outputs/charts/equity_curve.png", dpi=200, bbox_inches='tight')
    plt.show()
    
    print(f"✅ Equity curve saved to outputs/charts/equity_curve.png")
    print(f"   Total data points: {len(df)}")
    print(f"   Time range: {df['timestamp'].min()} → {df['timestamp'].max()}")

if __name__ == "__main__":
    plot_equity_curve()
