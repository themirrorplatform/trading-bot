"""
Signal Utilities - Reusable detector primitives for signal computation.

Extracted from bias/strategy framework and repurposed as signal building blocks.
These are pure functions that can be composed into more complex signals.
"""
from typing import Dict, Any, Optional
from decimal import Decimal
from collections import deque


def compute_impulse_strength(
    close: Decimal, 
    open_price: Decimal, 
    high: Decimal, 
    low: Decimal,
    atr: Optional[Decimal] = None
) -> float:
    """
    Measures directional strength of the bar.
    Returns [0.0 - 1.0] for bullish, [-1.0 - 0.0] for bearish.
    """
    if atr is None or atr == 0:
        range_size = high - low
        if range_size == 0:
            return 0.0
        atr = range_size
    
    body = close - open_price
    impulse = float(body / atr)
    return max(-1.0, min(1.0, impulse))


def compute_sweep_then_reject(
    high: Decimal,
    low: Decimal, 
    close: Decimal,
    prev_high: Optional[Decimal],
    prev_low: Optional[Decimal],
    threshold_ticks: Decimal = Decimal("2")
) -> float:
    """
    Detects liquidity sweep followed by rejection.
    Returns 1.0 if detected, 0.0 otherwise.
    """
    if prev_high is None or prev_low is None:
        return 0.0
    
    # Swept high then closed below
    if high > prev_high and close < (prev_high - threshold_ticks):
        return 1.0
    
    # Swept low then closed above
    if low < prev_low and close > (prev_low + threshold_ticks):
        return 1.0
    
    return 0.0


def compute_absorption_proxy(
    volume: int,
    range_size: Decimal,
    avg_volume: float,
    avg_range: float
) -> float:
    """
    Detects absorption: high volume + small range.
    Returns [0.0 - 1.0] absorption score.
    """
    if avg_volume == 0 or avg_range == 0:
        return 0.0
    
    volume_ratio = volume / avg_volume
    range_ratio = float(range_size) / avg_range
    
    # High volume, small range = absorption
    if volume_ratio > 1.5 and range_ratio < 0.5:
        return min(1.0, (volume_ratio - 1.0) * (1.0 - range_ratio))
    
    return 0.0


def compute_round_number_proximity(
    price: Decimal,
    round_levels: list[int] = None
) -> float:
    """
    Measures proximity to round number levels.
    Returns [0.0 - 1.0], 1.0 = at round number.
    """
    if round_levels is None:
        # Default MES levels
        round_levels = [5800, 5850, 5900, 5950, 6000, 6050, 6100]
    
    price_float = float(price)
    min_distance = min(abs(price_float - level) for level in round_levels)
    
    # Within 0.5% = strong proximity
    threshold = 0.005 * max(round_levels)
    if min_distance < threshold:
        return 1.0 - (min_distance / threshold)
    
    return 0.0


def compute_late_entry_flag(
    current_price: Decimal,
    entry_level: Decimal,
    target_level: Decimal
) -> float:
    """
    Detects if entry is >70% through expected move.
    Returns 1.0 if late, 0.0 if early.
    """
    total_move = abs(float(target_level - entry_level))
    if total_move == 0:
        return 0.0
    
    completed_move = abs(float(current_price - entry_level))
    completion_ratio = completed_move / total_move
    
    if completion_ratio > 0.7:
        return completion_ratio
    
    return 0.0


def compute_volatility_expansion(
    current_atr: Decimal,
    avg_atr: Decimal,
    threshold: float = 1.5
) -> float:
    """
    Detects volatility expansion above threshold.
    Returns [0.0 - 1.0] expansion score.
    """
    if avg_atr == 0:
        return 0.0
    
    ratio = float(current_atr / avg_atr)
    if ratio > threshold:
        return min(1.0, (ratio - threshold) / threshold)
    
    return 0.0


def compute_delta_divergence(
    price_change: Decimal,
    volume_change: float,
    threshold: float = 0.3
) -> float:
    """
    Detects price/volume divergence.
    Returns [0.0 - 1.0] divergence score.
    """
    price_direction = 1.0 if price_change > 0 else -1.0 if price_change < 0 else 0.0
    volume_direction = 1.0 if volume_change > 0 else -1.0 if volume_change < 0 else 0.0
    
    # Divergence = opposite directions
    if price_direction * volume_direction < 0:
        divergence = abs(float(price_change)) + abs(volume_change)
        return min(1.0, divergence / 2.0)
    
    return 0.0


def compute_fomo_index(
    impulse_strength: float,
    volume_surge: float,
    price_extension: float
) -> float:
    """
    FOMO indicator: strong impulse + volume surge + extended price.
    Returns [0.0 - 1.0] FOMO score.
    """
    # All components must be elevated
    if impulse_strength > 0.6 and volume_surge > 0.6 and price_extension > 0.6:
        return (impulse_strength + volume_surge + price_extension) / 3.0
    
    return 0.0


def compute_panic_index(
    volatility_expansion: float,
    absorption_score: float,
    impulse_strength: float
) -> float:
    """
    Panic/capitulation indicator: vol expansion + absorption + strong impulse.
    Returns [0.0 - 1.0] panic score.
    """
    # Panic = extreme vol + heavy volume + directional impulse
    if volatility_expansion > 0.7 and absorption_score > 0.5:
        return (volatility_expansion + absorption_score + abs(impulse_strength)) / 3.0
    
    return 0.0


def compute_auction_efficiency(
    close: Decimal,
    vwap: Decimal,
    volume: int,
    avg_volume: float
) -> float:
    """
    Measures how efficiently price found fair value.
    Returns [0.0 - 1.0], 1.0 = efficient (at VWAP with normal volume).
    """
    if vwap == 0 or avg_volume == 0:
        return 0.5
    
    price_deviation = abs(float((close - vwap) / vwap))
    volume_ratio = volume / avg_volume
    
    # Efficient = near VWAP + normal volume
    if price_deviation < 0.01 and 0.8 < volume_ratio < 1.2:
        return 1.0
    
    # Inefficient = away from VWAP or extreme volume
    inefficiency = price_deviation + abs(volume_ratio - 1.0)
    return max(0.0, 1.0 - inefficiency)


def compute_herding_score(
    consecutive_bars_same_direction: int,
    volume_trend: float,
    impulse_consistency: float
) -> float:
    """
    Detects herding behavior: sustained directional flow.
    Returns [0.0 - 1.0] herding score.
    """
    # Herding = many consecutive bars + rising volume + consistent impulse
    direction_factor = min(1.0, consecutive_bars_same_direction / 5.0)
    
    if volume_trend > 0.5 and impulse_consistency > 0.6:
        return (direction_factor + volume_trend + impulse_consistency) / 3.0
    
    return 0.0
