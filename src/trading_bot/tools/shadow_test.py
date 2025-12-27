from __future__ import annotations

import json

# Shadow parameter validation stub
# Per Section 11: parameter updates queue in shadow mode first
# Promotion requires: 30+ samples, outperform live by 5%, max DD increase < 2%, confidence 95%


class ShadowParameter:
    def __init__(self, name: str, current_value: float, proposed_value: float):
        self.name = name
        self.current_value = current_value
        self.proposed_value = proposed_value
        self.shadow_samples = 0
        self.shadow_pnl = 0.0
        self.live_pnl = 0.0
        self.shadow_dd = 0.0

    def update(self, shadow_result: float, live_result: float):
        self.shadow_samples += 1
        self.shadow_pnl += shadow_result
        self.live_pnl += live_result

    def can_promote(self) -> bool:
        if self.shadow_samples < 30:
            return False
        if self.shadow_pnl < self.live_pnl * 1.05:
            return False
        if self.shadow_dd > 0.02:
            return False
        return True


def test_shadow_promotion():
    # Simulate a parameter update: belief threshold from 0.60 to 0.58
    param = ShadowParameter("belief_threshold", 0.60, 0.58)

    # Simulate 30 trades: shadow slightly better
    for i in range(30):
        shadow = 1.0 if i % 5 != 0 else -1.0
        live = 1.0 if i % 6 != 0 else -1.0
        param.update(shadow, live)

    result = {
        "parameter": param.name,
        "current": param.current_value,
        "proposed": param.proposed_value,
        "samples": param.shadow_samples,
        "shadow_pnl": param.shadow_pnl,
        "live_pnl": param.live_pnl,
        "can_promote": param.can_promote(),
    }
    return result


if __name__ == "__main__":
    result = test_shadow_promotion()
    print(json.dumps(result, indent=2))
