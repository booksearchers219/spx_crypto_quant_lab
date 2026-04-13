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

        # === AGGRESSIVE + REBALANCE SETTINGS ===
        self.base_fraction = 0.28
        self.max_fraction_per_trade = 0.55
        self.min_trade_value = 300
        self.max_positions = 10
        self.rebalance_threshold = 1500      # If cash > this → trigger rebalance
        self.dca_threshold = 800             # Add to existing positions if cash > this

        if not self.load_state():
            self.cash = float(capital)
            print(f"ℹ️ Starting fresh {self.name} portfolio with ${self.cash:,.2f}")

    def should_rebalance(self):
        """Check if we should force deploy idle cash"""
        return self.cash > self.rebalance_threshold

    def calculate_position_size(self, current_price: float, signal_strength: float = 1.0):
        if self.cash < self.min_trade_value:
            return 0, 0

        base_allocation = self.cash * self.base_fraction * signal_strength
        allocation = min(base_allocation, self.cash * self.max_fraction_per_trade)
        allocation = max(allocation, self.min_trade_value)
        allocation = min(allocation, self.cash)

        quantity = allocation / current_price
        return quantity, allocation

    def open_position(self, ticker, entry_price, signal_strength: float = 1.0):
        if len(self.positions) >= self.max_positions and ticker not in self.positions:
            print(f"⚠️ Max positions reached. Trying DCA instead.")
            return self.add_to_position(ticker, entry_price, signal_strength)

        entry_price = float(entry_price)
        quantity, usd_amount = self.calculate_position_size(entry_price, signal_strength)

        if quantity <= 0:
            return False

        self.cash -= usd_amount

        if ticker in self.positions:
            # DCA: average down/up
            pos = self.positions[ticker]
            total_value = pos['quantity'] * pos['entry_price'] + usd_amount
            total_qty = pos['quantity'] + quantity
            pos['entry_price'] = total_value / total_qty
            pos['quantity'] = total_qty
            print(f"📈 DCA added to {ticker} | +${usd_amount:,.0f} | New Avg: ${pos['entry_price']:.4f}")
        else:
            self.positions[ticker] = {
                'entry_price': entry_price,
                'quantity': float(quantity),
                'peak_price': entry_price,
                'entry_time': time.time()
            }
            print(f"🟢 Opened NEW position {ticker} | ${usd_amount:,.0f} | Qty: {quantity:.6f}")

        self.save_state()
        return True

    def add_to_position(self, ticker, current_price, signal_strength=1.0):
        """Force DCA into an existing position"""
        if ticker not in self.positions:
            return False
        return self.open_position(ticker, current_price, signal_strength)

    def check_trailing_stop(self, ticker, current_price):
        if ticker not in self.positions:
            return False

        pos = self.positions[ticker]
        current_price = float(current_price)

        if current_price > pos.get('peak_price', pos['entry_price']):
            pos['peak_price'] = current_price

        trail_percent = 0.08
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
        value = float(self.cash)
        for ticker, pos in self.positions.items():
            price = current_prices.get(ticker, pos['entry_price'])
            if hasattr(price, 'iloc'):
                price = float(price.iloc[-1])
            else:
                price = float(price)
            value += float(pos.get('quantity', 0)) * price
        return value

    def save_state(self):
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
        except Exception as e:
            print(f"⚠️ Failed to save state: {e}")

    def load_state(self):
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
            print(f"⚠️ Failed to load state: {e}")
            return False