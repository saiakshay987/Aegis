"""
Aegis - High-Performance Day-by-Day Financial Simulation Engine
==============================================================
Phase 5 Implementation:
  - Maintains stateful per-user running balances & sliding transaction windows.
  - Incrementally updates rolling features per tick in O(1) time (no full re-scans).
  - Evaluates the retrained Random Forest distress classifier via vectorized batch inference.
  - Supports deterministic shock injection (POST /api/simulation/inject-shock).
  - Emits real-time simulation updates per user per day: {user_id, day, balance, risk_label, risk_score}.

Deployment:
  This is the CANONICAL copy at aegis/backend/ML_model/simulation/simulation_engine.py.
  Other locations (aegis/backend/simulation_engine.py) re-export from here.
"""

import os
import sys
import json
import sqlite3
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import deque
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# ── Path setup ──────────────────────────────────────────────────────────────
_SIMULATION_DIR = Path(__file__).resolve().parent           # .../ML_model/simulation
_ML_MODEL_DIR = _SIMULATION_DIR.parent                     # .../ML_model
_BACKEND_DIR = _ML_MODEL_DIR.parent                        # .../backend

if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from ledger import get_db_path

_MODELS_DIR = _ML_MODEL_DIR / "models"


class UserSimulationState:
    """Encapsulates running financial state for a single user."""
    def __init__(self, user_id: str, opening_balance: float, monthly_income: float, monthly_emi: float, scenario: str):
        self.user_id = user_id
        self.opening_balance = opening_balance
        self.monthly_income = monthly_income
        self.monthly_emi = monthly_emi
        self.scenario = scenario
        
        self.current_balance = opening_balance
        self.current_day = 0 # Day index (1..N)
        self.current_date: Optional[datetime] = None
        
        # Sliding deques: store (day_index, amount, is_essential, category)
        self.history_30d = deque()
        self.history_14d = deque()
        self.history_7d = deque()
        
        # Running sums
        self.essential_7d = 0.0
        self.essential_14d = 0.0
        self.essential_30d = 0.0
        self.spend_7d = 0.0
        self.spend_30d = 0.0
        self.inflow_30d = 0.0
        
        self.days_since_last_income = 15
        self.income_dates = deque(maxlen=6)
        self.anomaly_scores = deque(maxlen=30)
        
        # Output state
        self.risk_label = "healthy"
        self.risk_score = 15
        self.distress_prob = 0.15

    def add_transaction(self, day_idx: int, amount: float, category: str, is_essential: bool, anomaly_score: float = 0.0):
        """Append a transaction to the user's ledger and update running sums in O(1)."""
        self.current_balance += amount
        
        tx_tuple = (day_idx, amount, is_essential, category)
        self.history_30d.append(tx_tuple)
        self.history_14d.append(tx_tuple)
        self.history_7d.append(tx_tuple)
        
        if amount < 0:
            abs_amt = abs(amount)
            self.spend_30d += abs_amt
            self.spend_14d_temp = getattr(self, 'spend_14d_temp', 0.0) + abs_amt
            self.spend_7d += abs_amt
            if is_essential:
                self.essential_30d += abs_amt
                self.essential_14d += abs_amt
                self.essential_7d += abs_amt
        else:
            self.inflow_30d += amount
            if category in ["salary", "freelance_income", "upi_received"]:
                self.days_since_last_income = 0
                self.income_dates.append(day_idx)
                
        if anomaly_score > 0:
            self.anomaly_scores.append(anomaly_score)

    def expire_windows(self, current_day_idx: int):
        """Slide windows forward and evict transactions older than 7, 14, and 30 days in O(1)."""
        # Expire 7 days
        while self.history_7d and (current_day_idx - self.history_7d[0][0]) > 7:
            day, amt, is_ess, _ = self.history_7d.popleft()
            if amt < 0:
                self.spend_7d = max(0.0, self.spend_7d - abs(amt))
                if is_ess:
                    self.essential_7d = max(0.0, self.essential_7d - abs(amt))
                    
        # Expire 14 days
        while self.history_14d and (current_day_idx - self.history_14d[0][0]) > 14:
            day, amt, is_ess, _ = self.history_14d.popleft()
            if amt < 0 and is_ess:
                self.essential_14d = max(0.0, self.essential_14d - abs(amt))
                
        # Expire 30 days
        while self.history_30d and (current_day_idx - self.history_30d[0][0]) > 30:
            day, amt, is_ess, _ = self.history_30d.popleft()
            if amt < 0:
                self.spend_30d = max(0.0, self.spend_30d - abs(amt))
                if is_ess:
                    self.essential_30d = max(0.0, self.essential_30d - abs(amt))
            else:
                self.inflow_30d = max(0.0, self.inflow_30d - amt)

    def get_feature_vector(self) -> Dict[str, float]:
        """Extract instant feature vector for ML model inference."""
        daily_7d = self.spend_7d / 7.0
        daily_30d = self.spend_30d / 30.0
        spend_vel = round(daily_7d / (daily_30d + 1.0), 3)
        
        # Income regularity
        if len(self.income_dates) >= 2:
            diffs = [self.income_dates[i] - self.income_dates[i-1] for i in range(1, len(self.income_dates))]
            inc_reg = round(float(np.std(diffs)), 2)
        else:
            inc_reg = 30.0
            
        anom_mean = round(float(np.mean(self.anomaly_scores)), 4) if self.anomaly_scores else 0.0
        anom_count = len(self.anomaly_scores)
        emi_ratio = round(self.monthly_emi / (self.monthly_income + 1.0), 3)
        net_cf = round(self.inflow_30d - self.spend_30d, 2)
        
        return {
            "walked_balance": round(self.current_balance, 2),
            "monthly_income": self.monthly_income,
            "essential_expense_7d": round(self.essential_7d, 2),
            "essential_expense_14d": round(self.essential_14d, 2),
            "essential_expense_30d": round(self.essential_30d, 2),
            "spend_velocity_change": spend_vel,
            "income_regularity": inc_reg,
            "days_since_last_income": self.days_since_last_income,
            "anomaly_score_mean": anom_mean,
            "anomaly_count_30d": anom_count,
            "emi_burden_ratio": emi_ratio,
            "net_cashflow_30d": net_cf
        }


class SimulationEngine:
    """
    Day-by-Day Simulation Engine that manages all users across time ticks.
    
    Uses canonical get_db_path() for OS-agnostic database resolution and
    repo-relative model paths. No hardcoded absolute paths.
    """
    def __init__(self, db_path: Optional[str] = None, seed: int = 42):
        self.db_path = db_path or get_db_path()
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        
        # Load ML model & metadata from repo-relative paths
        model_dir = str(_MODELS_DIR)
        self.model = joblib.load(os.path.join(model_dir, "distress_classifier.pkl"))
        self.le = joblib.load(os.path.join(model_dir, "label_encoder.pkl"))
        with open(os.path.join(model_dir, "feature_order.json")) as f:
            self.feature_order = json.load(f)
            
        self.users: Dict[str, UserSimulationState] = {}
        self.injected_shocks: Dict[Tuple[str, int], List[Dict[str, Any]]] = {} # (uid, day_idx) -> list of shocks
        self.current_day = 0
        self.simulation_log: List[Dict[str, Any]] = []
        
        self._initialize_from_db()

    def _initialize_from_db(self):
        """Initializes user baseline state from database."""
        conn = sqlite3.connect(self.db_path)
        users_df = pd.read_sql("SELECT user_id, monthly_income, opening_balance, scenario FROM users", conn)
        loans_df = pd.read_sql("SELECT user_id, monthly_emi FROM loans", conn)
        tx_df = pd.read_sql("SELECT user_id, date, amount, category, is_essential FROM transactions ORDER BY date ASC", conn)
        tx_df['date'] = pd.to_datetime(tx_df['date'])
        conn.close()
        
        loans_map = {uid: df['monthly_emi'].sum() for uid, df in loans_df.groupby('user_id')}
        tx_map = {uid: df for uid, df in tx_df.groupby('user_id')}
        
        for _, row in users_df.iterrows():
            uid = row['user_id']
            emi = float(loans_map.get(uid, 0.0))
            user_state = UserSimulationState(
                user_id=uid,
                opening_balance=float(row['opening_balance']),
                monthly_income=float(row['monthly_income']),
                monthly_emi=emi,
                scenario=str(row.get('scenario', 'normal'))
            )
            
            # Pre-seed history with the last 30 days of baseline transactions
            user_tx = tx_map.get(uid, pd.DataFrame())
            if len(user_tx) > 0:
                max_d = user_tx['date'].max()
                past_30 = user_tx[user_tx['date'] > (max_d - timedelta(days=30))]
                for _, t_row in past_30.iterrows():
                    day_offset = (t_row['date'] - max_d).days # negative days relative to day 0
                    user_state.add_transaction(
                        day_idx=day_offset,
                        amount=float(t_row['amount']),
                        category=str(t_row['category']),
                        is_essential=bool(t_row['is_essential'])
                    )
                # Compute starting walked balance
                user_state.current_balance = float(row['opening_balance']) + user_tx['amount'].sum()
                
            self.users[uid] = user_state

    def inject_shock(self, user_id: str, day: int, amount: float, category: str, is_essential: bool = True):
        """
        Deterministically schedules an exogenous shock transaction at a specified simulated day.
        """
        key = (user_id, int(day))
        if key not in self.injected_shocks:
            self.injected_shocks[key] = []
            
        shock = {
            "user_id": user_id,
            "day": int(day),
            "amount": float(amount), # typically negative, e.g. -50000
            "category": category,
            "is_essential": is_essential,
            "anomaly_score": 0.85
        }
        self.injected_shocks[key].append(shock)
        return shock

    def step_day(self) -> List[Dict[str, Any]]:
        """
        Advances the entire 500-user portfolio by exactly 1 simulated day.
        Returns the batch update event for all users.
        """
        self.current_day += 1
        day_idx = self.current_day
        
        # 1. Update each user's transactions for today
        feature_rows = []
        user_list = list(self.users.values())
        
        for user in user_list:
            user.current_day = day_idx
            user.days_since_last_income += 1
            
            # Check for deterministic injected shocks
            shocks = self.injected_shocks.get((user.user_id, day_idx), [])
            for shock in shocks:
                user.add_transaction(
                    day_idx=day_idx,
                    amount=shock["amount"],
                    category=shock["category"],
                    is_essential=shock["is_essential"],
                    anomaly_score=shock.get("anomaly_score", 0.75)
                )
                
            # Generative baseline daily transaction (deterministic with self.rng)
            # Probability of daily spending: 70%
            if self.rng.rand() < 0.70:
                # Essential food/utilities
                spend_amt = -round(float(self.rng.gamma(shape=2.5, scale=250.0)), 2)
                user.add_transaction(day_idx=day_idx, amount=spend_amt, category="groceries", is_essential=True)
                
            # Periodic salary deposit on day 1 or 15
            if (day_idx % 30) == 1:
                user.add_transaction(day_idx=day_idx, amount=user.monthly_income, category="salary", is_essential=False)
                
            # Monthly EMI deduction on day 5
            if (day_idx % 30) == 5 and user.monthly_emi > 0:
                user.add_transaction(day_idx=day_idx, amount=-user.monthly_emi, category="loan_repayment", is_essential=True)
                
            # Expire windows older than 7/14/30 days
            user.expire_windows(day_idx)
            
            # Extract features
            f_vec = user.get_feature_vector()
            feature_rows.append(f_vec)

        # 2. Vectorized batch classification for all users
        X_batch = pd.DataFrame([[f[k] for k in self.feature_order] for f in feature_rows], columns=self.feature_order)
        probas = self.model.predict_proba(X_batch)
        preds = self.le.inverse_transform(self.model.predict(X_batch))
        
        # Map class names to indices
        class_names = list(self.le.classes_)
        crit_idx = class_names.index("critical") if "critical" in class_names else -1
        risk_idx = class_names.index("at_risk") if "at_risk" in class_names else -1
        
        day_events = []
        for i, user in enumerate(user_list):
            user.risk_label = str(preds[i])
            
            p_distress = 0.0
            if crit_idx >= 0:
                p_distress += probas[i][crit_idx]
            if risk_idx >= 0:
                p_distress += probas[i][risk_idx]
                
            user.distress_prob = round(float(p_distress), 4)
            user.risk_score = int(min(100, max(0, round(p_distress * 70 + (user.monthly_emi / (user.monthly_income + 1)) * 30))))
            
            event = {
                "user_id": user.user_id,
                "day": day_idx,
                "balance": round(user.current_balance, 2),
                "risk_label": user.risk_label,
                "risk_score": user.risk_score,
                "distress_probability": user.distress_prob
            }
            day_events.append(event)
            self.simulation_log.append(event)
            
        return day_events

    def run_days(self, num_days: int = 30) -> List[Dict[str, Any]]:
        """Advances the simulation by N days sequentially."""
        all_events = []
        for _ in range(num_days):
            all_events.extend(self.step_day())
        return all_events
