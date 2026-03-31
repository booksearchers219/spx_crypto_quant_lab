import json
import os
from datetime import datetime


class RiskManager:
    def __init__(self, capital: float = 30000):
        self.initial_capital = capital
        self.cash = capital
        self.positions = {}  # ticker -> {'quantity': qty, 'entry_price': price}
        self.trade_history = []
        self.load_state()

    def get_current_value(self, price_dict: dict) -> float:
        """Calculate total portfolio value (cash + positions)"""
        value = self.cash
        for ticker, pos in self.positions.items():
            if ticker in price_dict:
                value += pos['quantity'] * price_dict[ticker]
        return value

    def open_position(self, ticker: str, price: float, fraction: float = 0.98):
        """Open a virtual long position"""
        if ticker in self.positions:
            print(f"⚠️ Already in position for {ticker}")
            return False

        investment = self.cash * fraction
        quantity = investment / price

        self.positions[ticker] = {'quantity': quantity, 'entry_price': price}
        self.cash -= investment

        self._log_trade(ticker, "BUY", quantity, price)
        print(f"🟢 VIRTUAL BUY → {ticker} | Qty: {quantity:.6f} | Price: ${price:.4f}")
        return True

    def close_position(self, ticker: str, price: float):
        """Close virtual position"""
        if ticker not in self.positions:
            return False

        pos = self.positions[ticker]
        proceeds = pos['quantity'] * price
        self.cash += proceeds

        pnl = (price - pos['entry_price']) * pos['quantity']

        self._log_trade(ticker, "SELL", pos['quantity'], price, pnl)
        print(f"🔴 VIRTUAL SELL → {ticker} | Qty: {pos['quantity']:.6f} | Price: ${price:.4f} | P&L: ${pnl:.2f}")

        del self.positions[ticker]
        return True

    def _log_trade(self, ticker, action, quantity, price, pnl=0):
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
            "cash": self.cash,
            "positions": self.positions,
            "initial_capital": self.initial_capital,
            "last_updated": datetime.now().isoformat()
        }
        os.makedirs("outputs", exist_ok=True)
        with open("outputs/portfolio_state.json", "w") as f:
            json.dump(state, f, indent=4)

    def load_state(self):
        try:
            with open("outputs/portfolio_state.json", "r") as f:
                state = json.load(f)
                self.cash = state.get("cash", self.initial_capital)
                self.positions = state.get("positions", {})
        except:
            pass