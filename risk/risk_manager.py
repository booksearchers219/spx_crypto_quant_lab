import json
import os
from datetime import datetime
import time


class RiskManager:
    def __init__(self, capital=30000, name="crypto"):
        self.initial_capital = float(capital)
        self.name = name
        self.positions = {}
        self.trade_history = []
        self.state_file = f"outputs/portfolio_state_{self.name}.json"

        # Try to load previous state first (default behavior)
        if not self.load_state():
            # Only start fresh if no saved state exists
            self.cash = float(capital)
            print(f"ℹ️ Starting fresh {self.name} portfolio with ${self.cash:,.2f}")

    def reset(self):
        """Force reset to initial capital and clear all positions"""
        self.cash = float(self.initial_capital)
        self.positions = {}
        self.trade_history = []
        # Delete the state file so next run also starts fresh
        if os.path.exists(self.state_file):
            try:
                os.remove(self.state_file)
                print(f"🗑️  Deleted old state file for {self.name}")
            except Exception as e:
                print(f"⚠️ Could not delete state file: {e}")

        print(f"✅ {self.name.upper()} portfolio has been RESET to ${self.initial_capital:,.0f}")
        self.save_state()  # Save the reset state

    def open_position(self, ticker, entry_price, base_fraction=0.07, max_addons=2):
        entry_price = float(entry_price)
        allocation = self.cash * base_fraction

        if allocation < 50:  # minimum trade size
            print(f"⚠️ Not enough cash for {ticker} (allocation ${allocation:.2f})")
            return False

        quantity = allocation / entry_price
        self.cash -= allocation

        self.positions[ticker] = {
            'entry_price': entry_price,
            'quantity': float(quantity),
            'peak_price': entry_price
        }

        print(f"🟢 Opened position {ticker} | Qty: {quantity:.6f} | Entry: ${entry_price:.4f}")
        self.save_state()
        return True

    def check_trailing_stop(self, ticker, current_price):
        """Check trailing stop and close if triggered."""
        if ticker not in self.positions:
            return False

        pos = self.positions[ticker]
        current_price = float(current_price)

        # Update peak price if new high
        if current_price > pos.get('peak_price', pos['entry_price']):
            pos['peak_price'] = current_price

        # Trailing Stop Logic (7% by default - you can make this configurable later)
        trail_percent = 0.07
        stop_price = pos['peak_price'] * (1 - trail_percent)

        if current_price <= stop_price:
            self.close_position(ticker, current_price, reason="trailing_stop")
            return True
        return False

    def close_position(self, ticker, exit_price, reason="signal"):
        if ticker not in self.positions:
            return False

        pos = self.positions[ticker]
        exit_price = float(exit_price)
        pnl = (exit_price - pos['entry_price']) * pos['quantity']

        self.cash += pos['quantity'] * exit_price

        trade = {
            'ticker': ticker,
            'entry': pos['entry_price'],
            'exit': exit_price,
            'quantity': pos['quantity'],
            'pnl': pnl,
            'reason': reason,
            'timestamp': time.time()
        }
        self.trade_history.append(trade)

        print(f"🔴 Closed {ticker} | Exit: ${exit_price:.4f} | P&L: ${pnl:,.2f} | Reason: {reason}")

        del self.positions[ticker]
        self.save_state()
        return True

    def get_current_value(self, current_prices: dict) -> float:
        """Calculate total portfolio value including open positions"""
        value = float(self.cash)
        for ticker, pos in self.positions.items():
            price = current_prices.get(ticker, pos['entry_price'])
            # Safe price extraction
            if hasattr(price, 'iloc'):
                price = float(price.iloc[-1])
            else:
                price = float(price)
            value += float(pos.get('quantity', 0)) * price
        return value

    def save_state(self):
        """Save current portfolio state to disk"""
        state = {
            "name": self.name,
            "cash": float(self.cash),
            "positions": self.positions,
            "initial_capital": float(self.initial_capital),
            "last_updated": datetime.now().isoformat()
        }
        try:
            os.makedirs("outputs", exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=4)
            # Optional: print only on manual runs, not every 15min
        except Exception as e:
            print(f"⚠️ Failed to save {self.name} state: {e}")

    def load_state(self):
        """Load previous portfolio state if file exists"""
        if not os.path.exists(self.state_file):
            return False

        try:
            with open(self.state_file, "r") as f:
                state = json.load(f)

            self.cash = float(state.get("cash", self.initial_capital))
            self.positions = state.get("positions", {})
            self.initial_capital = float(state.get("initial_capital", self.initial_capital))

            print(f"✅ Loaded previous {self.name} state — Cash: ${self.cash:,.2f} | Positions: {len(self.positions)}")
            return True
        except Exception as e:
            print(f"⚠️ Failed to load {self.name} state: {e}")
            return False