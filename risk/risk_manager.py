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

    def get_current_value(self, price_dict: dict) -> float:
        value = self.cash
        for ticker, pos in self.positions.items():
            if ticker in price_dict:
                price = price_dict[ticker]
                price = float(price.iloc[0]) if hasattr(price, 'iloc') else float(price)
                value += float(pos['quantity']) * price
        return value

    def open_position(self, ticker: str, price, fraction: float = 0.12):
        if ticker in self.positions:
            return False

        price = float(price.iloc[0]) if hasattr(price, 'iloc') else float(price)
        investment = self.cash * fraction
        if investment < 100:
            return False

        quantity = investment / price

        self.positions[ticker] = {
            'quantity': float(quantity),
            'entry_price': float(price)
        }
        self.cash -= investment

        self._log_trade(ticker, "BUY", quantity, price)
        print(f"🟢 VIRTUAL BUY → {ticker} | Qty: {quantity:.6f} | Price: ${price:.4f} | Invested: ${investment:,.2f}")
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