import json
import os
from datetime import datetime
import time


class RiskManager:
    def __init__(self, capital=80000, name="crypto"):
        self.initial_capital = float(capital)
        self.name = name
        self.positions = {}
        self.trade_history = []
        self.state_file = f"outputs/portfolio_state_{self.name}.json"

        # === Balanced & Safe Settings ===
        self.base_risk_per_trade = 0.008   # 0.8% of capital per trade
        self.max_risk_per_trade = 0.015    # 1.5% max
        self.max_portfolio_risk = 0.08     # 8% total at risk
        self.min_trade_value = 800
        self.max_positions = 8 if name == "crypto" else 6

        self.trailing_stop_pct = 0.045     # 4.5% from peak
        self.hard_stop_pct = 0.09          # 9% from entry

        # Daily risk control
        self.daily_loss_limit = 0.025      # Max 2.5% loss per day
        self.daily_pnl = 0.0
        self.current_date = datetime.now().date()

        if not self.load_state():
            self.cash = float(capital)
            print(f"ℹ️ Starting fresh {self.name} portfolio with ${self.cash:,.2f}")

    def reset(self):
        self.initial_capital = 80000.0
        self.cash = float(self.initial_capital)
        self.positions = {}
        self.trade_history = []
        self.daily_pnl = 0.0
        if os.path.exists(self.state_file):
            try:
                os.remove(self.state_file)
            except:
                pass
        self.save_state()
        print(f"✅ {self.name.upper()} Portfolio Reset to ${self.cash:,.0f}")

    def _check_new_day(self):
        today = datetime.now().date()
        if today != self.current_date:
            self.daily_pnl = 0.0
            self.current_date = today

    def calculate_position_size(self, current_price: float, atr: float = None, signal_strength: float = 1.0):
        self._check_new_day()
        if self.cash < self.min_trade_value:
            return 0, 0

        risk_amount = self.initial_capital * self.base_risk_per_trade * signal_strength
        risk_amount = min(risk_amount, self.initial_capital * self.max_risk_per_trade)

        if atr and atr > 0:
            stop_distance = max(atr * 2.0, current_price * 0.03)
            quantity = risk_amount / stop_distance
        else:
            quantity = risk_amount / (current_price * 0.045)

        quantity = min(quantity, (self.cash * 0.25) / current_price)
        usd_amount = quantity * current_price

        return max(quantity, 0), min(usd_amount, self.cash)

    def open_position(self, ticker, entry_price, atr=None, signal_strength: float = 1.0):
        self._check_new_day()
        if self.daily_pnl <= -self.initial_capital * self.daily_loss_limit:
            print(f"⚠️ Daily loss limit hit ({self.daily_pnl:,.0f}). No new positions today.")
            return False

        if len(self.positions) >= self.max_positions and ticker not in self.positions:
            return self.add_to_position(ticker, entry_price, atr, signal_strength)

        entry_price = float(entry_price)
        quantity, usd_amount = self.calculate_position_size(entry_price, atr, signal_strength)

        if quantity <= 0 or usd_amount < self.min_trade_value:
            return False

        self.cash -= usd_amount

        if ticker in self.positions:
            pos = self.positions[ticker]
            total_value = pos['quantity'] * pos['entry_price'] + usd_amount
            total_qty = pos['quantity'] + quantity
            pos['entry_price'] = total_value / total_qty
            pos['quantity'] = total_qty
            print(f"📈 DCA added to {ticker} | +${usd_amount:,.0f}")
        else:
            self.positions[ticker] = {
                'entry_price': entry_price,
                'quantity': float(quantity),
                'peak_price': entry_price,
                'entry_time': time.time(),
                'atr_at_entry': atr
            }
            print(f"🟢 Opened {ticker} | ${usd_amount:,.0f} | Qty: {quantity:.4f}")

        self.save_state()
        return True

    def add_to_position(self, ticker, current_price, atr=None, signal_strength=1.0):
        if ticker not in self.positions:
            return False
        return self.open_position(ticker, current_price, atr, signal_strength)

    def check_trailing_stop(self, ticker, current_price):
        if ticker not in self.positions:
            return False

        pos = self.positions[ticker]
        current_price = float(current_price)

        if current_price > pos.get('peak_price', pos['entry_price']):
            pos['peak_price'] = current_price

        trail_stop = pos['peak_price'] * (1 - self.trailing_stop_pct)
        hard_stop = pos['entry_price'] * (1 - self.hard_stop_pct)

        if current_price <= max(trail_stop, hard_stop):
            reason = "trailing_stop" if current_price <= trail_stop else "hard_stop"
            self.close_position(ticker, current_price, reason=reason)
            return True
        return False

    def close_position(self, ticker, exit_price, reason="signal"):
        if ticker not in self.positions:
            return False

        pos = self.positions[ticker]
        exit_price = float(exit_price)
        pnl = (exit_price - pos['entry_price']) * pos['quantity']

        self.cash += pos['quantity'] * exit_price
        self.daily_pnl += pnl

        trade = {'ticker': ticker, 'entry': pos['entry_price'], 'exit': exit_price,
                 'quantity': pos['quantity'], 'pnl': pnl, 'reason': reason,
                 'timestamp': time.time()}
        self.trade_history.append(trade)

        print(f"🔴 Closed {ticker} | Exit: ${exit_price:.4f} | P&L: ${pnl:,.2f} | {reason}")

        del self.positions[ticker]
        self.save_state()
        return True

    def get_current_value(self, current_prices: dict) -> float:
        value = float(self.cash)
        for ticker, pos in self.positions.items():
            price = current_prices.get(ticker, pos['entry_price'])
            price = float(price.iloc[-1]) if hasattr(price, 'iloc') else float(price)
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
            print(f"✅ Loaded {self.name} state — Cash: ${self.cash:,.2f} | Positions: {len(self.positions)}")
            return True
        except Exception as e:
            print(f"⚠️ Failed to load state: {e}")
            return False