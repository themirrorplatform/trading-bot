"""Component 4: Decision Engine v1.

Implements hierarchy per constitution.yaml:
Kill switch > Constitution > DVS/EQS > Regime > Capital > Belief+Stability > Friction > Template.

Outputs DECISION_1M payload:
- If NO_TRADE: includes machine-readable no_trade_reason (see reason_codes.py)
- If TRADE: emits ORDER_INTENT payload (separate event type)

v1 simplifications:
- Single strategy template (F1_MEAN_REVERSION)
- Manual template selection
- Fixed position sizing (1 contract)
- No adaptive stops/targets
"""
from __future__ import annotations

from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, time
from dataclasses import dataclass

from ..core.reason_codes import NoTradeReason
from ..core.config import load_yaml_contract


@dataclass
class OrderIntent:
    """Order intent payload for execution layer."""
    direction: str  # "LONG" or "SHORT"
    contracts: int
    entry_type: str  # "MARKET" or "LIMIT"
    stop_ticks: int
    target_ticks: int
    stop_order_type: str
    target_order_type: str
    strategy_id: str
    timestamp: datetime
    metadata: Dict[str, Any]


class DecisionEngine:
    """
    Decision engine that evaluates strategy templates per constitution hierarchy.
    """
    
    def __init__(self, contracts_path: str = "src/trading_bot/contracts"):
        self.contracts_path = contracts_path
        self.strategy_templates = load_yaml_contract(contracts_path, "strategy_templates.yaml")
        self.constitution = load_yaml_contract(contracts_path, "constitution.yaml")
        self.session = load_yaml_contract(contracts_path, "session.yaml")
        
        # Active template (v1: single template)
        self.active_template_id = self.strategy_templates["template_metadata"]["default_template"]
        self.active_template = self._get_template(self.active_template_id)
    
    def _get_template(self, template_id: str) -> Dict[str, Any]:
        """Get strategy template by ID."""
        for template in self.strategy_templates["strategy_templates"]:
            if template["id"] == template_id:
                return template
        raise ValueError(f"Template {template_id} not found")
    
    def decide(
        self,
        signals: Dict[str, Any],
        state: Dict[str, Any],
        risk_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main decision function.
        
        Args:
            signals: Output from SignalEngine (session_phase, vwap_distance, atr14, etc.)
            state: Bot state (position, DVS, EQS, etc.)
            risk_state: RiskEngine state (kill_switch, daily_pnl, etc.)
        
        Returns:
            {"action": "NO_TRADE", "reason": NoTradeReason, ...} or
            {"action": "ORDER_INTENT", "intent": OrderIntent, ...}
        """
        # Use provided state timestamp when available for deterministic tests
        timestamp = state.get("timestamp", datetime.now())
        
        # 1. Kill switch check (highest priority)
        if risk_state.get("kill_switch_active", False):
            return {
                "action": "NO_TRADE",
                "reason": NoTradeReason.KILL_SWITCH_ACTIVE,
                "timestamp": timestamp.isoformat(),
                "metadata": {"kill_switch_reason": risk_state.get("kill_switch_reason")}
            }
        
        # 2. Constitution gates (DVS, EQS)
        dvs = state.get("dvs", Decimal("0"))
        eqs = state.get("eqs", Decimal("0"))
        
        dvs_threshold = Decimal(str(self.constitution["dvs_gates"]["min_dvs_for_entry"]))
        eqs_threshold = Decimal(str(self.constitution["eqs_gates"]["min_eqs_for_entry"]))
        
        if dvs < dvs_threshold:
            return {
                "action": "NO_TRADE",
                "reason": NoTradeReason.DVS_TOO_LOW,
                "timestamp": timestamp.isoformat(),
                "metadata": {"dvs": float(dvs), "threshold": float(dvs_threshold)}
            }
        
        if eqs < eqs_threshold:
            return {
                "action": "NO_TRADE",
                "reason": NoTradeReason.EQS_TOO_LOW,
                "timestamp": timestamp.isoformat(),
                "metadata": {"eqs": float(eqs), "threshold": float(eqs_threshold)}
            }
        
        # 3. Session/time gates
        session_phase = signals.get("session_phase_code", 0)
        current_time = timestamp.time()
        
        # Check no-trade windows per session.yaml
        for window in self.session["no_trade_windows"]:
            if not window.get("enabled", False):
                continue
            start = datetime.strptime(window["start_time"], "%H:%M").time()
            end = datetime.strptime(window["end_time"], "%H:%M").time()
            if start <= current_time < end:
                return {
                    "action": "NO_TRADE",
                    "reason": NoTradeReason.SESSION_WINDOW_BLOCK,
                    "timestamp": timestamp.isoformat(),
                    "metadata": {"window": window["id"], "reason": window.get("reason", "")}
                }
        
        # 4. Frequency & position checks
        # Max trades per day
        trades_today = risk_state.get("trades_today", 0)
        # Pull threshold from risk_model if available
        try:
            risk_model = load_yaml_contract(self.contracts_path, "risk_model.yaml")
            max_trades_per_day = int(risk_model.get("per_day_risk", {}).get("max_trades_per_day", 10))
        except Exception:
            max_trades_per_day = 10
        if trades_today >= max_trades_per_day:
            return {
                "action": "NO_TRADE",
                "reason": NoTradeReason.MAX_TRADES_REACHED,
                "timestamp": timestamp.isoformat(),
                "metadata": {"trades_today": trades_today, "limit": max_trades_per_day}
            }

        # Cooldown: min minutes between entries (from constitution frequency_limits)
        last_entry_time = risk_state.get("last_entry_time")
        if last_entry_time is not None:
            try:
                cooldown_minutes = int(self.constitution.get("frequency_limits", {}).get("min_minutes_between_entries", 30))
            except Exception:
                cooldown_minutes = 30
            delta_minutes = int((timestamp - last_entry_time).total_seconds() // 60)
            if delta_minutes < cooldown_minutes:
                return {
                    "action": "NO_TRADE",
                    "reason": NoTradeReason.COOLDOWN_ACTIVE,
                    "timestamp": timestamp.isoformat(),
                    "metadata": {"elapsed_minutes": delta_minutes, "required_minutes": cooldown_minutes}
                }

        # Consecutive loss lockout
        consecutive_losses = int(risk_state.get("consecutive_losses", 0))
        try:
            risk_model = load_yaml_contract(self.contracts_path, "risk_model.yaml")
            max_consecutive_losses = int(risk_model.get("per_day_risk", {}).get("max_consecutive_losses", 3))
        except Exception:
            max_consecutive_losses = 3
        if consecutive_losses >= max_consecutive_losses:
            return {
                "action": "NO_TRADE",
                "reason": NoTradeReason.CONSECUTIVE_LOSS_LOCKOUT,
                "timestamp": timestamp.isoformat(),
                "metadata": {"consecutive_losses": consecutive_losses}
            }

        # Position check (v1: single position limit)
        position = state.get("position", 0)
        if position != 0:
            return {
                "action": "NO_TRADE",
                "reason": NoTradeReason.IN_POSITION,
                "timestamp": timestamp.isoformat(),
                "metadata": {"position": position}
            }
        
        # 5. Daily risk limits
        daily_pnl = risk_state.get("daily_pnl", Decimal("0"))
        daily_loss_limit = Decimal(str(self.constitution["drawdown_limits"]["max_daily_loss_usd"]))
        
        if daily_pnl <= -daily_loss_limit:
            return {
                "action": "NO_TRADE",
                "reason": NoTradeReason.DAILY_LOSS_LIMIT,
                "timestamp": timestamp.isoformat(),
                "metadata": {"daily_pnl": float(daily_pnl), "limit": float(daily_loss_limit)}
            }
        
        # 6. Evaluate strategy template entry conditions
        # Fail-closed preflight: required signals must be present
        required_signals = ["vwap", "atr14", "spread_ticks"]
        missing = [k for k in required_signals if signals.get(k) is None]
        if missing:
            return {
                "action": "NO_TRADE",
                "reason": NoTradeReason.MISSING_REQUIRED_SIGNAL,
                "timestamp": timestamp.isoformat(),
                "metadata": {"missing_signals": missing}
            }

        template_result = self._evaluate_template_entry(
            self.active_template,
            signals,
            state,
            risk_state
        )
        
        if template_result["passed"]:
            # Generate order intent
            intent = self._create_order_intent(
                self.active_template,
                signals,
                state,
                timestamp
            )
            # FRICTION gate: pessimistic execution cost vs expected move to T1
            slippage_ticks = int(signals.get("slippage_estimate_ticks", 0) or 0)
            spread_ticks = int(signals.get("spread_ticks", 0) or 0)
            friction_ticks = slippage_ticks + spread_ticks
            expected_move_ticks = int(self.active_template.get("stop_target", {}).get("target_ticks", 8))
            if expected_move_ticks > 0:
                friction_share = friction_ticks / expected_move_ticks
                if friction_share > 0.30:
                    return {
                        "action": "NO_TRADE",
                        "reason": NoTradeReason.FRICTION_TOO_HIGH,
                        "timestamp": timestamp.isoformat(),
                        "metadata": {
                            "slippage_ticks": slippage_ticks,
                            "spread_ticks": spread_ticks,
                            "friction_ticks": friction_ticks,
                            "expected_move_ticks": expected_move_ticks,
                            "share": friction_share
                        }
                    }
            return {
                "action": "ORDER_INTENT",
                "intent": intent,
                "timestamp": timestamp.isoformat(),
                "metadata": {
                    "strategy_id": self.active_template_id,
                    "signals": self._extract_signal_snapshot(signals)
                }
            }
        else:
            return {
                "action": "NO_TRADE",
                "reason": template_result["reason"],
                "timestamp": timestamp.isoformat(),
                "metadata": template_result["metadata"]
            }
    
    def _evaluate_template_entry(
        self,
        template: Dict[str, Any],
        signals: Dict[str, Any],
        state: Dict[str, Any],
        risk_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate all entry conditions for a strategy template.
        
        Returns:
            {"passed": bool, "reason": Optional[str], "metadata": Dict}
        """
        entry_conditions = template["entry_conditions"]
        
        for condition in entry_conditions:
            if not condition.get("required", False):
                continue  # Skip optional conditions in v1
            
            result = self._evaluate_condition(condition, signals, state, risk_state)
            if not result["passed"]:
                return {
                    "passed": False,
                    "reason": result.get("reason", NoTradeReason.CONDITION_NOT_MET),
                    "metadata": {
                        "condition_id": condition["id"],
                        "condition_type": condition["type"],
                        "details": result.get("metadata", {})
                    }
                }
        
        return {"passed": True, "reason": None, "metadata": {}}
    
    def _evaluate_condition(
        self,
        condition: Dict[str, Any],
        signals: Dict[str, Any],
        state: Dict[str, Any],
        risk_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate a single condition.
        
        Returns:
            {"passed": bool, "reason": Optional[str], "metadata": Dict}
        """
        cond_type = condition["type"]
        
        # Session phase conditions
        if cond_type == "session_phase_eq":
            phase = signals.get("session_phase_code", 0)
            expected = condition["value"]
            passed = (phase == expected)
            return {
                "passed": passed,
                "reason": NoTradeReason.CONDITION_NOT_MET if not passed else None,
                "metadata": {"phase": phase, "expected": expected}
            }
        
        # Price vs VWAP conditions
        elif cond_type == "price_vs_vwap_lt":
            vwap = signals.get("vwap")
            price = state.get("last_price")
            if vwap is None or price is None:
                return {"passed": False, "reason": NoTradeReason.MISSING_REQUIRED_SIGNAL, "metadata": {}}
            
            vwap_pct = ((price - vwap) / vwap) * Decimal("100")
            threshold = Decimal(str(condition["threshold"]))
            passed = vwap_pct < threshold
            return {
                "passed": passed,
                "reason": NoTradeReason.CONDITION_NOT_MET if not passed else None,
                "metadata": {"vwap_pct": float(vwap_pct), "threshold": float(threshold)}
            }
        
        # ATR normalized range
        elif cond_type == "atr_norm_range":
            atr14 = signals.get("atr14")
            if atr14 is None:
                return {"passed": False, "reason": NoTradeReason.MISSING_REQUIRED_SIGNAL, "metadata": {}}
            
            # Normalize ATR by price (ATR / Price as percentage)
            price = state.get("last_price", Decimal("5000"))
            atr_norm = (atr14 / price) * Decimal("100")
            
            min_val = Decimal(str(condition["min"]))
            max_val = Decimal(str(condition["max"]))
            passed = min_val <= atr_norm <= max_val
            return {
                "passed": passed,
                "reason": NoTradeReason.CONDITION_NOT_MET if not passed else None,
                "metadata": {"atr_norm": float(atr_norm), "min": float(min_val), "max": float(max_val)}
            }
        
        # Spread conditions
        elif cond_type == "spread_ticks_lte":
            spread = signals.get("spread_ticks")
            if spread is None:
                return {"passed": False, "reason": NoTradeReason.MISSING_REQUIRED_SIGNAL, "metadata": {}}
            
            max_spread = condition["value"]
            passed = spread <= max_spread
            return {
                "passed": passed,
                "reason": NoTradeReason.SPREAD_TOO_WIDE if not passed else None,
                "metadata": {"spread": spread, "max": max_spread}
            }
        
        # DVS gate
        elif cond_type == "dvs_gte":
            dvs = state.get("dvs", Decimal("0"))
            threshold = Decimal(str(condition["threshold"]))
            passed = dvs >= threshold
            return {
                "passed": passed,
                "reason": NoTradeReason.DVS_TOO_LOW if not passed else None,
                "metadata": {"dvs": float(dvs), "threshold": float(threshold)}
            }
        
        # EQS gate
        elif cond_type == "eqs_gte":
            eqs = state.get("eqs", Decimal("0"))
            threshold = Decimal(str(condition["threshold"]))
            passed = eqs >= threshold
            return {
                "passed": passed,
                "reason": NoTradeReason.EQS_TOO_LOW if not passed else None,
                "metadata": {"eqs": float(eqs), "threshold": float(threshold)}
            }
        
        # Position check
        elif cond_type == "position_eq":
            position = state.get("position", 0)
            expected = condition["value"]
            passed = (position == expected)
            return {
                "passed": passed,
                "reason": NoTradeReason.IN_POSITION if not passed else None,
                "metadata": {"position": position, "expected": expected}
            }
        
        # Unknown condition type - fail closed
        else:
            return {
                "passed": False,
                "reason": "UNKNOWN_CONDITION_TYPE",
                "metadata": {"type": cond_type}
            }
    
    def _create_order_intent(
        self,
        template: Dict[str, Any],
        signals: Dict[str, Any],
        state: Dict[str, Any],
        timestamp: datetime
    ) -> OrderIntent:
        """Create order intent from template parameters."""
        # v1: Always LONG for mean reversion below VWAP
        direction = "LONG"
        
        # Position sizing
        contracts = template["position_sizing"]["fixed_size"]
        
        # Stop/target from template
        stop_ticks = template["stop_target"]["stop_ticks"]
        target_ticks = template["stop_target"]["target_ticks"]
        stop_order_type = template["stop_target"]["stop_order_type"]
        target_order_type = template["stop_target"]["target_order_type"]
        
        return OrderIntent(
            direction=direction,
            contracts=contracts,
            entry_type="MARKET",  # v1 simplification
            stop_ticks=stop_ticks,
            target_ticks=target_ticks,
            stop_order_type=stop_order_type,
            target_order_type=target_order_type,
            strategy_id=template["id"],
            timestamp=timestamp,
            metadata={
                "vwap": float(signals.get("vwap", 0)),
                "atr14": float(signals.get("atr14", 0)),
                "session_phase": signals.get("session_phase_code", 0)
            }
        )
    
    def _extract_signal_snapshot(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key signals for decision metadata."""
        return {
            "session_phase_code": signals.get("session_phase_code"),
            "vwap": float(signals.get("vwap", 0)) if signals.get("vwap") else None,
            "atr14": float(signals.get("atr14", 0)) if signals.get("atr14") else None,
            "spread_ticks": signals.get("spread_ticks")
        }
