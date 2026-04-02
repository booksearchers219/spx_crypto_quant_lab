import json
import os
from datetime import datetime


class RiskManager:
    def __init__(self, capital: float = 30000, name: str = "default"):
        self.name = name
        self.initial_capital = float(capital)
        self.cash = float(capital)
        self.positions = {}
        self.trade_history = []
        self.load_state()

    def reset(self):
        """Reset portfolio back to initial $30,000"""
        self.cash = float(self.initial_capital)
        self.positions = {}
        self.trade_history = []
        self.save_state()
        print(f"🔄 {self.name.upper()} Portfolio RESET to ${self.initial_capital:,.2f}")

    def get_current_value(self, price_dict: dict) -> float:
        value = float(self.cash)
        for ticker, pos in self.positions.items():
            if ticker in price_dict:
                price = price_dict[ticker]
                price = float(price.iloc[0]) if hasattr(price, 'iloc') else float(price)
                value += float(pos['quantity']) * price
        return value

    def open_position(self, ticker: str, price, base_fraction: float = 0.15, max_addons: int = 3):
        """
        Open or add to a position.
        - New position: uses base_fraction of current cash (increased from 0.12 to 0.15)
        - Add-on: uses smaller size (60% of base) up to max_addons total entries per ticker
        """
        price = float(price.iloc[0].item() if hasattr(price, 'iloc') else price)

        # Calculate current entries for this ticker
        if ticker in self.positions:
            current_count = self.positions[ticker].get('entry_count', 1)
            if current_count >= max_addons:
                print(f"   ⚠️  Max entries reached for {ticker} ({current_count}/{max_addons})")
                return False
            fraction = base_fraction * 0.60  # Smaller add-on (~9% of cash)
            action = "ADD"
        else:
            fraction = base_fraction  # New position: 15% of cash
            action = "BUY"
            current_count = 0

        investment = self.cash * fraction
        if investment < 100:
            print(f"   ⚠️  Investment too small for {ticker} (${investment:.2f})")
            return False

        quantity = investment / price

        if ticker not in self.positions:
            # First entry
            self.positions[ticker] = {
                'quantity': float(quantity),
                'entry_price': float(price),  # will become average on adds
                'entry_count': 1
            }
        else:
            # Add to existing position (weighted average entry)
            pos = self.positions[ticker]
            total_qty = pos['quantity'] + quantity
            weighted_entry = (pos['entry_price'] * pos['quantity'] + price * quantity) / total_qty

            pos['quantity'] = float(total_qty)
            pos['entry_price'] = float(weighted_entry)
            pos['entry_count'] = current_count + 1

        self.cash -= investment
        self._log_trade(ticker, "BUY", quantity, price)

        print(f"🟢 VIRTUAL {action} → {ticker} | Qty: {quantity:.6f} | Price: ${price:.4f} | "
              f"Invested: ${investment:,.2f} | Cash left: ${self.cash:,.2f}")

        return True
    def close_position(self, ticker: str, price):
        if ticker not in self.positions:
            return False

        price = float(price.iloc[0]) if hasattr(price, 'iloc') else float(price)
        pos = self.positions[ticker]
        proceeds = pos['quantity'] * price
        self.cash += proceeds
        pnl = (price - pos['entry_price']) * pos['quantity']

        self._log_trade(ticker, "SELL", pos['quantity'], price, pnl)
        print(f"🔴 VIRTUAL SELL → {ticker} | Qty: {pos['quantity']:.6f} | Price: ${price:.4f} | P&L: ${pnl:.2f}")

        del self.positions[ticker]
        return True

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