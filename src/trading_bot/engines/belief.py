"""Component 3: Belief Engine (stub).

Computes constraint beliefs (Tier 1 at minimum) using:
- constraint-signal matrix weights
- per-constraint decay rates (lambda)
- normalization within tier
- stability = EWMA(|Δp|)

Outputs BELIEFS_1M payload:
{
  "beliefs": {"F1": 0.61, ...},          # in [0, 1]
  "stability": {"F1": 0.08, ...},        # in [0, 1] lower = more stable
  "top_constraints": ["F1","F4","F3"]
}
"""
from __future__ import annotations

from typing import Dict, Any


def _clamp01(x: float) -> float:
  return max(0.0, min(1.0, x))


def _normalize_signal(signal_name: str, value: Any, norms: Dict[str, Any]) -> float:
  try:
    v = float(value)
  except (TypeError, ValueError):
    return 0.0
  spec = norms.get(signal_name) if isinstance(norms, dict) else None
  if isinstance(spec, dict):
    mn = float(spec.get("min", 0.0))
    mx = float(spec.get("max", 1.0))
    if mx == mn:
      return 0.0
    return _clamp01((v - mn) / (mx - mn))
  # Fallback: clamp value assumed already in [0,1]
  return _clamp01(v)


def update_beliefs(signals_payload: Dict[str, Any], prev_beliefs: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
  """
  Compute Tier-1 constraint beliefs from signals with decay, normalization, and stability EWMA.

  cfg shape (typical):
  {
    "constraints": [
    {"id": "F1", "weights": {"vwap_distance_pct": 0.5, "atr_norm_pct": 0.5}, "decay_lambda": 0.1},
    {"id": "F2", "weights": {"momentum_pct": 1.0}, "decay_lambda": 0.05}
    ],
    "signal_norms": {"vwap_distance_pct": {"min": -2.0, "max": 2.0}, "atr_norm_pct": {"min": 0.2, "max": 1.2}},
    "stability": {"alpha": 0.2}
  }
  """

  constraints = cfg.get("constraints", []) or []
  norms = cfg.get("signal_norms", {}) or {}
  normalize_mode = (cfg.get("normalize_mode") or "independent").lower()

  beliefs: Dict[str, float] = {}

  # Compute raw beliefs from weighted normalized signals
  for c in constraints:
    cid = c.get("id")
    weights = c.get("weights", {}) or {}
    decay_lambda = float(c.get("decay_lambda", 0.0) or 0.0)
    if not cid or not isinstance(weights, dict) or len(weights) == 0:
      continue
    score = 0.0
    total_w = 0.0
    for sig, w in weights.items():
      try:
        wv = float(w)
      except (TypeError, ValueError):
        continue
      total_w += max(0.0, wv)
      norm_val = _normalize_signal(sig, signals_payload.get(sig), norms)
      score += max(0.0, wv) * norm_val
    if total_w > 0.0:
      score /= total_w
    # Apply decay to previous belief
    prev = float(prev_beliefs.get("beliefs", {}).get(cid, 0.0) or 0.0) if isinstance(prev_beliefs, dict) else 0.0
    blended = (1.0 - decay_lambda) * score + decay_lambda * prev
    beliefs[cid] = _clamp01(blended)

  # Optional tier normalization
  if normalize_mode == "softmax" and len(beliefs) > 0:
    import math
    vals = list(beliefs.values())
    max_v = max(vals)
    exps = {k: math.exp(v - max_v) for k, v in beliefs.items()}
    z = sum(exps.values())
    if z > 0:
      beliefs = {k: exps[k] / z for k in beliefs}
  elif normalize_mode == "sum1" and len(beliefs) > 0:
    s = sum(beliefs.values())
    if s > 0:
      beliefs = {k: v / s for k, v in beliefs.items()}
    # Clamp to [0,1]
    beliefs = {k: _clamp01(v) for k, v in beliefs.items()}

  # Stability = EWMA(|Δp|) in [0,1] with naive normalization
  stab_cfg = cfg.get("stability", {}) or {}
  alpha = float(stab_cfg.get("alpha", 0.2) or 0.2)
  last_price = signals_payload.get("last_price")
  prev_price = (prev_beliefs or {}).get("_prev_price")
  try:
    lp = float(last_price) if last_price is not None else None
    pp = float(prev_price) if prev_price is not None else None
  except (TypeError, ValueError):
    lp, pp = None, None

  if lp is not None and pp is not None and lp > 0.0:
    delta_pct = abs(lp - pp) / max(pp, 1e-9)
    # Naive cap at 5% move for normalization
    norm_delta = _clamp01(delta_pct / 0.05)
  else:
    norm_delta = 0.0

  prev_stability = (prev_beliefs or {}).get("stability", {})
  stability: Dict[str, float] = {}
  for cid in beliefs.keys():
    prev_s = float(prev_stability.get(cid, 0.0) or 0.0)
    stability[cid] = _clamp01(alpha * norm_delta + (1.0 - alpha) * prev_s)

  # Top constraints by belief
  top_constraints = sorted(beliefs.keys(), key=lambda k: beliefs[k], reverse=True)

  return {
    "beliefs": beliefs,
    "stability": stability,
    "top_constraints": top_constraints,
    "_prev_price": last_price,
  }
