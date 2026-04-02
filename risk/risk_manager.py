import json
import os
from datetime import datetime
import time

class RiskManager:
    def __init__(self, capital=30000, name="crypto"):
        self.initial_capital = float(capital)
        self.cash = float(capital)
        self.positions = {}      # ticker -> dict with entry_price, quantity, peak_price
        self.name = name
        self.trade_history = []

    def reset(self):
        self.cash = float(self.initial_capital)
        self.positions = {}
        self.trade_history = []
        print(f"✅ {self.name.upper()} portfolio has been RESET to ${self.initial_capital:,.0f}")

    def open_position(self, ticker, entry_price, base_fraction=0.07, max_addons=2):
        entry_price = float(entry_price)
        allocation = self.cash * base_fraction

        if allocation < 50:   # minimum trade size
            return False

        quantity = allocation / entry_price

        self.cash -= allocation

        self.positions[ticker] = {
            'entry_price': entry_price,
            'quantity': float(quantity),
            'peak_price': entry_price,      # <-- Used for trailing stop
        }
        print(f"   🟢 Opened position {ticker} | Qty: {quantity:.6f} | Entry: ${entry_price:.4f}")
        return True

    def check_trailing_stop(self, ticker, current_price):
        """Check trailing stop and close if triggered."""
        if ticker not in self.positions:
            return False

        pos = self.positions[ticker]
        current_price = float(current_price)

        # Update peak price if we hit a new high
        if current_price > pos.get('peak_price', pos['entry_price']):
            pos['peak_price'] = current_price

        # === Trailing Stop Logic ===
        trail_percent = 0.07          # ← Start with 7% (you can change this)
        stop_price = pos['peak_price'] * (1 - trail_percent)

        if current_price <= stop_price:
            self.close_position(ticker, current_price, reason="trailing_stop")
            return True
        return False

    def close_position(self, ticker, exit_price, reason="signal"):
        if ticker not in self.positions:
            return

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

        print(f"   🔴 Closed {ticker} | Exit: ${exit_price:.4f} | P&L: ${pnl:,.2f} | Reason: {reason}")
        del self.positions[ticker]

    def get_current_value(self, current_prices):
        total = self.cash
        for ticker, pos in self.positions.items():
            price = current_prices.get(ticker, pos['entry_price'])
            total += pos['quantity'] * float(price)
        return total

    def get_current_value(self, price_dict: dict) -> float:
        value = float(self.cash)
        for ticker, pos in self.positions.items():
            if ticker in price_dict:
                price = price_dict[ticker]
                # Safe conversion
                if hasattr(price, 'iloc'):
                    price = float(price.iloc[0].item() if hasattr(price.iloc[0], 'item') else price.iloc[0])
                else:
                    price = float(price)
                value += float(pos.get('quantity', 0)) * price
        return value




    def _log_trade(self, ticker, action, quantity, price, pnl=0.0):
        trade = {
            "timestamp": datetime.now().isoformat(),
            "ticker": ticker,
            "action": action,
            "quantity": float(quantity),
            "price": float(price),
            "pnl": float(pnl)
        }
        self.trade_history.append(trade)
        self.save_state()

    def save_state(self):
        state = {
            "name": self.name,
            "cash": float(self.cash),
            "positions": self.positions,
            "initial_capital": float(self.initial_capital),
            "last_updated": datetime.now().isoformat()
        }
        os.makedirs("outputs", exist_ok=True)
        with open(f"outputs/portfolio_state_{self.name}.json", "w") as f:
            json.dump(state, f, indent=4)

    def load_state(self):
        try:
            with open(f"outputs/portfolio_state_{self.name}.json", "r") as f:
                state = json.load(f)
                self.cash = float(state.get("cash", self.initial_capital))
                self.positions = state.get("positions", {})
        except:
            pass