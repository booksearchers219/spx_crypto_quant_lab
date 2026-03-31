#!/bin/bash

# Kill any existing session with same name
tmux kill-session -t quantlab 2>/dev/null

echo "🚀 Starting SPX + Crypto Quant Lab in Tmux..."

tmux new-session -d -s quantlab

# Left pane: Crypto Bot (24/7)
tmux rename-window 'Crypto Bot'
tmux send-keys "cd ~/spx_crypto_quant_lab && python -m live_trading.crypto_bot" C-m

# Split vertically and start Equity Bot on the right
tmux split-window -h
tmux send-keys "cd ~/spx_crypto_quant_lab && python -m live_trading.equity_bot" C-m

# Make panes even
tmux select-pane -t 0
tmux split-window -v "echo '📊 Dashboard Commands:'; echo 'python -m main --mode dashboard'; echo ''; echo 'Press Ctrl+B then D to detach'"

echo "✅ Tmux session started: 'quantlab'"
echo ""
echo "To attach:   tmux attach -t quantlab"
echo "To detach:   Ctrl+B then D"
echo "To kill:     tmux kill-session -t quantlab"
