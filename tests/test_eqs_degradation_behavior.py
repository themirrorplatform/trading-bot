from __future__ import annotations

from trading_bot.engines.dvs_eqs import compute_eqs


def test_eqs_degrades_on_slippage_ratio_rule():
    contract = {
        "eqs": {
            "initial_value": 1.0,
            "degradation_events": [
                {
                    "id": "slippage_high",
                    "condition": {"slippage_vs_expected_gt": 2.0},
                    "penalties": {"eqs_delta": -0.10},
                }
            ],
        }
    }
    state = {
        "eqs": 1.0,
        "fill_price": 100.5,
        "limit_price": 99.5,
        "expected_slippage": 0.4,  # |100.5-99.5| / 0.4 = 2.5 > 2.0
    }
    eqs = compute_eqs(state, contract)
    assert abs(eqs - 0.9) < 1e-9


def test_eqs_slippage_ratio_handles_zero_expected_slippage():
    contract = {
        "eqs": {
            "initial_value": 1.0,
            "degradation_events": [
                {
                    "id": "slippage_high",
                    "condition": {"slippage_vs_expected_gt": 2.0},
                    "penalties": {"eqs_delta": -0.10},
                }
            ],
        }
    }
    # expected_slippage = 0 triggers EPS floor; ratio becomes large and should trigger
    state = {
        "eqs": 1.0,
        "fill_price": 100.5,
        "limit_price": 100.0,
        "expected_slippage": 0,
    }
    eqs = compute_eqs(state, contract)
    assert abs(eqs - 0.9) < 1e-9
