"""
Data ingestion facade and DVS evaluation for MES survival bot.

This module:
1. Ingests bars and validates structure
2. Evaluates DVS using structured events from data_contract.yaml
3. Gates trading based on session/calendar/DVS thresholds
4. Provides fail-closed behavior on data quality issues
"""

from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional, Dict, Any, List
from decimal import Decimal

from ..core.config import Contracts


@dataclass(frozen=True)
class Bar:
    """
    OHLCV bar with timestamp and validation metadata.
    All prices as Decimal for precision.
    """
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    symbol: str


@dataclass(frozen=True)
class DataQualityReport:
    """
    DVS score and validation results for a bar.
    """
    dvs: float  # 0.0 to 1.0
    bar_valid: bool
    rejected_checks: List[str]  # List of failed validation IDs
    degradation_events: Dict[str, Any]  # Event ID -> penalty details


class DataLayer:
    """
    Data ingestion and DVS evaluation.
    """
    
    def __init__(self, contracts: Contracts):
        self.contracts = contracts
        self.data_contract = contracts.docs["data_contract.yaml"]
        self.session_contract = contracts.docs["session.yaml"]
        self.calendar_contract = contracts.docs["calendar.yaml"]
        
        # Pre-validate data contract structure
        if "dvs" not in self.data_contract:
            raise ValueError("data_contract.yaml missing 'dvs' section")
        if "degradation_events" not in self.data_contract["dvs"]:
            raise ValueError("data_contract.yaml missing 'dvs.degradation_events' list")
        
    def validate_bar(self, bar: Bar) -> DataQualityReport:
        """
        Validate bar structure and compute DVS.
        
        Returns DataQualityReport with:
        - dvs: quality score 0.0-1.0
        - bar_valid: True if bar passes all fail-closed checks
        - rejected_checks: list of failed validation IDs
        - degradation_events: dict of triggered events with penalties
        """
        rejected = []
        
        # OHLC sanity checks
        if not (bar.low <= bar.open <= bar.high):
            rejected.append("ohlc_open_range")
        if not (bar.low <= bar.close <= bar.high):
            rejected.append("ohlc_close_range")
        if not (bar.low <= bar.high):
            rejected.append("ohlc_low_high")
        
        # Volume sanity
        if bar.volume < 0:
            rejected.append("volume_negative")
        
        # If any fail-closed check fails, reject bar
        bar_valid = len(rejected) == 0
        
        # Compute DVS using structured events
        dvs_score = self._compute_dvs(bar, rejected)
        
        return DataQualityReport(
            dvs=dvs_score,
            bar_valid=bar_valid,
            rejected_checks=rejected,
            degradation_events={}  # TODO: populate with triggered events
        )
    
    def _compute_dvs(self, bar: Bar, rejected_checks: List[str]) -> float:
        """
        Compute DVS using structured degradation events.
        
        If bar failed fail-closed checks, return 0.0.
        Otherwise evaluate each event and accumulate penalties.
        """
        if rejected_checks:
            # Bar failed structural validation -> DVS = 0.0
            return 0.0
        
        # Bar passed structural checks, now evaluate DVS events
        dvs_cfg = self.data_contract["dvs"]
        events = dvs_cfg.get("degradation_events", [])
        
        # Start from initial DVS value
        dvs_val = float(dvs_cfg.get("initial_value", 1.0))
        
        # Build observed metrics dict from bar data
        observed = self._extract_dvs_events(bar)
        
        # Evaluate each event in order
        for event in events:
            if not isinstance(event, dict):
                continue
            
            # Check if condition matches
            condition = event.get("condition")
            if self._matches_condition(condition, observed):
                # Apply penalty
                dvs_val = self._apply_dvs_penalty(dvs_val, event)
        
        # Clamp to [0, 1]
        return max(0.0, min(1.0, dvs_val))
    
    def _matches_condition(self, cond: Any, metrics: Dict[str, Any]) -> bool:
        """
        Evaluate structured condition against observed metrics.
        Supports _gte, _gt, _lte, _lt, _eq suffixes.
        Unknown shapes fail-closed (False).
        """
        if cond is None:
            return False
        
        if isinstance(cond, dict):
            for key, val in cond.items():
                if key.endswith("_gte"):
                    metric = key[:-4]
                    if metrics.get(metric) is None or float(metrics[metric]) < float(val):
                        return False
                elif key.endswith("_gt"):
                    metric = key[:-3]
                    if metrics.get(metric) is None or float(metrics[metric]) <= float(val):
                        return False
                elif key.endswith("_lte"):
                    metric = key[:-4]
                    if metrics.get(metric) is None or float(metrics[metric]) > float(val):
                        return False
                elif key.endswith("_lt"):
                    metric = key[:-3]
                    if metrics.get(metric) is None or float(metrics[metric]) >= float(val):
                        return False
                elif key.endswith("_eq"):
                    metric = key[:-3]
                    if metrics.get(metric) != val:
                        return False
                else:
                    return False
            return True
        
        # Fail-closed for non-dict conditions
        return False
    
    def _apply_dvs_penalty(self, dvs: float, event: Dict[str, Any]) -> float:
        """Apply DVS penalty from triggered event."""
        if "immediate_penalty" in event:
            delta = float(event.get("immediate_penalty", 0.0))
            return dvs - delta
        
        penalties = event.get("penalties", {})
        if isinstance(penalties, dict):
            delta = float(penalties.get("dvs_delta", 0.0))
            return dvs + delta
        
        return dvs
    
    def _extract_dvs_events(self, bar: Bar) -> Dict[str, Any]:
        """
        Extract DVS event triggers from bar data.
        
        Returns dict with event values for matching:
        - spread_bps: (high - low) / close * 10000
        - volume: bar.volume
        - gap_bps: if available, gap from prior close
        """
        observed = {}
        
        # Spread in basis points
        spread = (bar.high - bar.low) / bar.close * Decimal(10000)
        observed["spread_bps"] = float(spread)
        
        # Volume
        observed["volume"] = bar.volume
        
        # Gap (if we track prior close, otherwise skip)
        # For now, omit gap calculation (requires state)
        
        return observed
    
    def is_trading_allowed(self, current_time: datetime, dvs: float) -> bool:
        """
        Check if trading is allowed based on session, calendar, DVS.
        
        Fail-closed: if any check is ambiguous, return False.
        """
        # Check calendar (holiday or half-day)
        if not self._is_market_open(current_time):
            return False
        
        # Check session no-trade windows
        if self._in_no_trade_window(current_time):
            return False
        
        # Check DVS threshold
        dvs_threshold = self.data_contract["dvs"].get("min_dvs_for_trading", 0.70)
        if dvs < dvs_threshold:
            return False
        
        return True
    
    def _is_market_open(self, current_time: datetime) -> bool:
        """Check if current date is a trading day."""
        date_str = current_time.strftime("%Y-%m-%d")
        
        # Check holidays (normalized as sorted list)
        holiday_dates = self.calendar_contract.get("holiday_dates", [])
        if date_str in holiday_dates:
            return False
        
        # Check if half-day and past close
        half_days = self.calendar_contract.get("half_days", [])
        for hd in half_days:
            if hd["date"] == date_str:
                # Parse close time (format: "HH:MM")
                close_parts = hd["close_time"].split(":")
                close_hour = int(close_parts[0])
                close_min = int(close_parts[1])
                close_time = time(close_hour, close_min)
                
                if current_time.time() >= close_time:
                    return False
        
        return True
    
    def _in_no_trade_window(self, current_time: datetime) -> bool:
        """Check if current time falls in a no-trade window."""
        no_trade_windows = self.session_contract.get("no_trade_windows", [])
        current_time_only = current_time.time()
        
        for window in no_trade_windows:
            if not window.get("enabled", False):
                continue
            
            # Parse start/end times
            start_parts = window["start_time"].split(":")
            end_parts = window["end_time"].split(":")
            
            start_time = time(int(start_parts[0]), int(start_parts[1]))
            end_time = time(int(end_parts[0]), int(end_parts[1]))
            
            if start_time <= current_time_only < end_time:
                return True
        
        return False
