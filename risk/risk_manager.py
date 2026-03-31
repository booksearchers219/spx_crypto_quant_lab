import pandas as pd
import json
import os
from datetime import datetime
from config.settings import DEFAULT_RISK_PER_TRADE, MAX_POSITIONS_EQUITY, MAX_POSITIONS_CRYPTO

class RiskManager:
    def __init__(self, capital: float = 10000):
        self.capital = capital
        self.positions = {}
        self.equity_curve = []
        self.load_state()
    
    def get_position_size(self, ticker: str, current_price: float, stop_loss_pct: float = 0.02):
        """Calculate safe position size (1% risk per trade)"""
        risk_amount = self.capital * DEFAULT_RISK_PER_TRADE
        position_size = risk_amount / (stop_loss_pct * current_price)
        return round(position_size, 6)  # for crypto precision
    
    def update_equity(self, new_value: float):
        self.equity_curve.append(new_value)
        self.save_state()
    
    def can_open_new_position(self, market_type: str = "equity"):
        max_pos = MAX_POSITIONS_EQUITY if market_type == "equity" else MAX_POSITIONS_CRYPTO
        return len(self.positions) < max_pos
    
    def save_state(self):
        state = {
            "capital": self.capital,
            "positions": self.positions,
            "equity_curve": self.equity_curve[-500:],  # keep last 500 points
            "last_updated": datetime.now().isoformat()
        }
        os.makedirs("outputs", exist_ok=True)
        with open("outputs/portfolio_state.json", "w") as f:
            json.dump(state, f, indent=4)
    
    def load_state(self):
        try:
            with open("outputs/portfolio_state.json", "r") as f:
                state = json.load(f)
                self.capital = state.get("capital", self.capital)
                self.positions = state.get("positions", {})
                self.equity_curve = state.get("equity_curve", [])
        except:
            pass
