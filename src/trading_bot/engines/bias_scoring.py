"""
Bias scoring functions - compute strength and confidence for each bias type.

Each function receives:
- detectors: Dict[str, float] - detector scores
- signals: Dict[str, Any] - raw signals
- context: Dict[str, Any] - historical context

Returns: float [0.0 - 1.0]
"""
from typing import Dict, Any


def trend_strength(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute trend bias strength."""
    impulse = detectors.get("impulse_strength", 0.0)
    breaks = detectors.get("breaks_level_high", 0.0)
    momentum = signals.get("F5", 0.5)
    
    # Weighted combination
    return (impulse * 0.5) + (breaks * 0.3) + (abs(momentum - 0.5) * 2 * 0.2)


def trend_confidence(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute trend bias confidence."""
    # Higher confidence when multiple detectors agree
    impulse = detectors.get("impulse_strength", 0.0)
    breaks = detectors.get("breaks_level_high", 0.0)
    consistency = signals.get("F1", 0.5)
    
    return min(1.0, (impulse + breaks + abs(consistency - 0.5) * 2) / 3.0)


def range_strength(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute range bias strength."""
    compression = detectors.get("range_compression", 0.0)
    vwap_dev = detectors.get("vwap_deviation", 0.0)
    
    # Strong range = high compression, low deviation from VWAP
    return (compression * 0.6) + ((1.0 - vwap_dev) * 0.4)


def range_confidence(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute range bias confidence."""
    compression = detectors.get("range_compression", 0.0)
    return compression  # Simple confidence = compression level


def reversion_strength(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute mean reversion bias strength."""
    vwap_dev = detectors.get("vwap_deviation", 0.0)
    compression = detectors.get("range_compression", 0.0)
    
    # Strong reversion = high deviation in compressed environment
    return (vwap_dev * 0.7) + (compression * 0.3)


def reversion_confidence(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute mean reversion bias confidence."""
    vwap_dev = detectors.get("vwap_deviation", 0.0)
    value_score = signals.get("F4", 0.5)
    
    # Confidence increases with deviation
    return min(1.0, vwap_dev + abs(value_score - 0.5) * 2)


def breakout_strength(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute breakout bias strength."""
    breaks = detectors.get("breaks_level_high", 0.0)
    vol_exp = detectors.get("volatility_expansion", 0.0)
    impulse = detectors.get("impulse_strength", 0.0)
    
    # All three needed for strong breakout
    return (breaks * 0.4) + (vol_exp * 0.3) + (impulse * 0.3)


def breakout_confidence(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute breakout bias confidence."""
    breaks = detectors.get("breaks_level_high", 0.0)
    impulse = detectors.get("impulse_strength", 0.0)
    
    # Confidence = agreement between break and impulse
    return (breaks + impulse) / 2.0


def vol_expansion_strength(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute volatility expansion bias strength."""
    vol_exp = detectors.get("volatility_expansion", 0.0)
    impulse = detectors.get("impulse_strength", 0.0)
    
    return (vol_exp * 0.7) + (impulse * 0.3)


def vol_expansion_confidence(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute volatility expansion bias confidence."""
    return detectors.get("volatility_expansion", 0.0)


def sweep_reversal_strength(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute liquidity sweep reversal bias strength."""
    sweep = detectors.get("sweep_then_reject", 0.0)
    vwap_dev = detectors.get("vwap_deviation", 0.0)
    
    return (sweep * 0.8) + (vwap_dev * 0.2)


def sweep_reversal_confidence(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute liquidity sweep reversal bias confidence."""
    return detectors.get("sweep_then_reject", 0.0)


def stop_run_strength(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute stop run bias strength."""
    breaks = detectors.get("breaks_level_high", 0.0)
    sweep = detectors.get("sweep_then_reject", 0.0)
    
    return (breaks * 0.5) + (sweep * 0.5)


def stop_run_confidence(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute stop run bias confidence."""
    sweep = detectors.get("sweep_then_reject", 0.0)
    return sweep


def absorption_strength(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute absorption bias strength."""
    absorption = detectors.get("absorption_proxy", 0.0)
    divergence = detectors.get("delta_divergence", 0.0)
    
    return (absorption * 0.6) + (divergence * 0.4)


def absorption_confidence(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute absorption bias confidence."""
    return detectors.get("absorption_proxy", 0.0)


def ny_open_strength(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute NY open volatility bias strength."""
    session = detectors.get("session_transition_ny_open", 0.0)
    vol_exp = detectors.get("volatility_expansion", 0.0)
    
    return session * vol_exp


def ny_open_confidence(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute NY open volatility bias confidence."""
    session = detectors.get("session_transition_ny_open", 0.0)
    return session


def london_open_strength(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute London open expansion bias strength."""
    session = detectors.get("session_transition_london_open", 0.0)
    vol_exp = detectors.get("volatility_expansion", 0.0)
    
    return session * vol_exp


def london_open_confidence(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute London open expansion bias confidence."""
    session = detectors.get("session_transition_london_open", 0.0)
    return session


def midday_reversion_strength(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute midday reversion bias strength."""
    vwap_dev = detectors.get("vwap_deviation", 0.0)
    compression = detectors.get("range_compression", 0.0)
    
    return (vwap_dev * 0.5) + (compression * 0.5)


def midday_reversion_confidence(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute midday reversion bias confidence."""
    compression = detectors.get("range_compression", 0.0)
    return compression


def power_hour_strength(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute power hour trend bias strength."""
    impulse = detectors.get("impulse_strength", 0.0)
    breaks = detectors.get("breaks_level_high", 0.0)
    
    return (impulse * 0.6) + (breaks * 0.4)


def power_hour_confidence(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute power hour trend bias confidence."""
    return detectors.get("impulse_strength", 0.0)


def panic_strength(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute panic selling bias strength."""
    impulse = detectors.get("impulse_strength", 0.0)
    vol_exp = detectors.get("volatility_expansion", 0.0)
    
    # Panic = extreme impulse + volatility spike
    return min(1.0, (impulse + vol_exp) / 2.0 * 1.3)


def panic_confidence(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute panic selling bias confidence."""
    vol_exp = detectors.get("volatility_expansion", 0.0)
    return vol_exp


def fomo_strength(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute FOMO bias strength."""
    impulse = detectors.get("impulse_strength", 0.0)
    breaks = detectors.get("breaks_level_high", 0.0)
    
    return (impulse * 0.7) + (breaks * 0.3)


def fomo_confidence(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute FOMO bias confidence."""
    return detectors.get("impulse_strength", 0.0)


def round_number_strength(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute round number magnet bias strength."""
    vwap_dev = detectors.get("vwap_deviation", 0.0)
    near_round = context.get("near_round_number", 0.0)
    
    return vwap_dev * near_round


def round_number_confidence(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute round number magnet bias confidence."""
    return context.get("near_round_number", 0.0)


def crowding_strength(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute strategy crowding bias strength."""
    divergence = detectors.get("delta_divergence", 0.0)
    absorption = detectors.get("absorption_proxy", 0.0)
    
    return (divergence * 0.6) + (absorption * 0.4)


def crowding_confidence(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute strategy crowding bias confidence."""
    return detectors.get("delta_divergence", 0.0)


def false_cascade_strength(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute false signal cascade bias strength."""
    sweep = detectors.get("sweep_then_reject", 0.0)
    divergence = detectors.get("delta_divergence", 0.0)
    
    return (sweep * 0.7) + (divergence * 0.3)


def false_cascade_confidence(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute false signal cascade bias confidence."""
    return detectors.get("sweep_then_reject", 0.0)


def vacuum_strength(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute liquidity vacuum bias strength."""
    vol_exp = detectors.get("volatility_expansion", 0.0)
    absorption = detectors.get("absorption_proxy", 0.0)
    
    # Vacuum = extreme vol but no absorption (no counterparty)
    return vol_exp * (1.0 - absorption)


def vacuum_confidence(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute liquidity vacuum bias confidence."""
    return detectors.get("volatility_expansion", 0.0)


def dead_market_strength(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute dead market bias strength."""
    compression = detectors.get("range_compression", 0.0)
    return compression


def dead_market_confidence(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute dead market bias confidence."""
    return detectors.get("range_compression", 0.0)


def silence_strength(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute market silence bias strength."""
    compression = detectors.get("range_compression", 0.0)
    vwap_dev = detectors.get("vwap_deviation", 0.0)
    
    # Silence = compression + price stuck near VWAP
    return (compression * 0.7) + ((1.0 - vwap_dev) * 0.3)


def silence_confidence(detectors: Dict[str, float], signals: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Compute market silence bias confidence."""
    return detectors.get("range_compression", 0.0)
