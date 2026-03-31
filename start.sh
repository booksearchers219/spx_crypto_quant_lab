#!/bin/bash
echo "============================================"
echo "   SPX + Crypto Quant Lab - Simplified Start"
echo "============================================"

echo "🔬 Running research once for both markets..."
python -m main --mode research --research_mode equity
python -m main --mode research --research_mode crypto

echo ""
echo "🚀 Starting both virtual trading bots..."
echo "   • Crypto bot  → Running 24/7"
echo "   • Equity bot  → Running during market hours"
echo ""
echo "Press Ctrl+C in this terminal to stop everything."
echo ""

# Start both bots in background
python -m live_trading.crypto_bot &
python -m live_trading.equity_bot &

wait
