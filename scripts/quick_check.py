import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from trading_bot.engines.dvs_eqs import compute_dvs, compute_eqs
from trading_bot.engines.belief import update_beliefs
from trading_bot.engines.attribution import attribute
from trading_bot.engines.simulator import simulate_fills

# Basic DVS test
state_dvs = {
    "bar_lag_seconds": 2,
    "missing_fields": 0,
    "gap_detected": False,
}
contract_data = {
    "dvs": {
        "initial_value": 1.0,
        "degradation_events": [
            {"id": "lag_high", "condition": {"bar_lag_seconds_gte": 3}, "immediate_penalty": 0.2},
            {"id": "gap", "condition": {"gap_detected_eq": True}, "immediate_penalty": 0.5},
        ],
        "recovery": {"dvs_recovery_per_bar": 0.05},
    }
}
print("DVS:", compute_dvs(state_dvs, contract_data))

# Basic EQS test
state_eqs = {
    "fill_price": 100.0,
    "limit_price": 99.5,
    "expected_slippage": 0.5,
    "order_state": "FILLED",
    "connection_state": "OK",
}
contract_exec = {
    "eqs": {
        "initial_value": 1.0,
        "degradation_events": [
            {"id": "high_slip", "condition": {"slippage_vs_expected_gte": 1.5}, "penalties": {"eqs_delta": -0.3}},
        ],
        "recovery": {"eqs_recovery_per_bar": 0.02},
        "slippage_min_expected": 1e-6,
    }
}
print("EQS:", compute_eqs(state_eqs, contract_exec))

# Beliefs test
signals_payload = {"vwap_distance_pct": -0.5, "atr_norm_pct": 0.4, "last_price": 100.0}
prev_beliefs = {"beliefs": {"F1": 0.6}, "stability": {"F1": 0.1}, "_prev_price": 99.0}
belief_cfg = {
    "constraints": [{"id": "F1", "weights": {"vwap_distance_pct": 0.5, "atr_norm_pct": 0.5}, "decay_lambda": 0.1}],
    "signal_norms": {"vwap_distance_pct": {"min": -2.0, "max": 2.0}, "atr_norm_pct": {"min": 0.0, "max": 1.0}},
    "stability": {"alpha": 0.2}
}
print("BELIEFS:", update_beliefs(signals_payload, prev_beliefs, belief_cfg))

# Attribution test
trade_record = {
    "entry_price": 100.0,
    "exit_price": 100.8,
    "pnl_usd": 40.0,
    "duration_seconds": 90,
    "slippage_ticks": 1,
    "spread_ticks": 2,
    "eqs": 0.9,
    "dvs": 0.95,
}
attr_cfg = {
    "rules": [
        {"id": "A1_FAST_REVERSION", "condition": {"duration_seconds_lte": 120, "pnl_usd_gt": 0}, "process_score": 0.8, "outcome_score": 0.9},
        {"id": "A2_LOSS_FAST", "condition": {"duration_seconds_lte": 120, "pnl_usd_lt": 0}, "process_score": 0.4, "outcome_score": 0.1},
    ],
    "default": {"id": "A0_UNCLASSIFIED", "process_score": 0.5, "outcome_score": 0.5}
}
print("ATTR:", attribute(trade_record, attr_cfg))

# Simulator test
intent = {"direction": "LONG", "contracts": 1}
market = {"last_price": 100.0, "spread_ticks": 2}
sim_cfg = {"tick_size": 0.25, "slippage_ticks": 1, "spread_to_slippage_ratio": 0.5}
print("SIM:", simulate_fills(intent, market, sim_cfg))
