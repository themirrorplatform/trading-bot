"""
Live Trading Runner - Production orchestrator for live trading.

Integrates:
- TradovateLiveAdapter for order execution
- TradovateDataFeed for real-time market data
- EventPublisher for Supabase sync
- V2 Engines (signals, beliefs, decision)
- Health monitoring and alerting
- Kill switch enforcement
"""

from __future__ import annotations

import os
import time
import signal
import logging
import threading
from typing import Dict, Any, Optional, Callable
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone
from enum import Enum

from trading_bot.adapters.tradovate_live import (
    TradovateLiveAdapter,
    TradovateConfig,
    TradovateEnvironment,
)
from trading_bot.adapters.data_feed import TradovateDataFeed, Bar
from trading_bot.log.event_publisher import EventPublisher, TradePublisher
from trading_bot.log.event_store import EventStore
from trading_bot.engines.signals_v2 import SignalEngineV2, ET
from trading_bot.engines.belief_v2 import BeliefEngineV2
from trading_bot.engines.decision_v2 import DecisionEngineV2
from trading_bot.engines.dvs_eqs import compute_dvs, compute_eqs
from trading_bot.core.state_store import StateStore
from trading_bot.core.types import Event, stable_json, sha256_hex
from trading_bot.core.config import load_yaml_contract
from trading_bot.log.decision_journal import DecisionJournal, DecisionRecord

logger = logging.getLogger(__name__)


class RunnerState(Enum):
    """Runner lifecycle states."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class HealthCheck:
    """Health monitoring for live trading."""

    def __init__(
        self,
        max_bars_without_trade: int = 60,  # 1 hour of no activity
        max_position_age_minutes: int = 120,  # 2 hours max position hold
        max_consecutive_errors: int = 5,
        alert_callback: Optional[Callable[[str, str], None]] = None,
    ):
        self.max_bars_without_trade = max_bars_without_trade
        self.max_position_age_minutes = max_position_age_minutes
        self.max_consecutive_errors = max_consecutive_errors
        self.alert_callback = alert_callback

        # Counters
        self._bars_processed = 0
        self._bars_since_trade = 0
        self._consecutive_errors = 0
        self._last_error: Optional[str] = None
        self._last_bar_time: Optional[datetime] = None
        self._position_entry_time: Optional[datetime] = None

        # Stats
        self._start_time = datetime.now(timezone.utc)
        self._trades_today = 0
        self._errors_today = 0

    def record_bar(self) -> None:
        """Record bar processed."""
        self._bars_processed += 1
        self._bars_since_trade += 1
        self._last_bar_time = datetime.now(timezone.utc)
        self._consecutive_errors = 0

    def record_trade(self) -> None:
        """Record trade placed."""
        self._bars_since_trade = 0
        self._trades_today += 1
        self._position_entry_time = datetime.now(timezone.utc)

    def record_exit(self) -> None:
        """Record position exit."""
        self._position_entry_time = None

    def record_error(self, error: str) -> None:
        """Record an error."""
        self._consecutive_errors += 1
        self._errors_today += 1
        self._last_error = error

    def check(self, position: int) -> Dict[str, Any]:
        """
        Run health checks.

        Returns:
            Dict with health status and any warnings/alerts
        """
        issues = []
        status = "healthy"

        # Check for data gaps
        if self._last_bar_time:
            gap = (datetime.now(timezone.utc) - self._last_bar_time).total_seconds()
            if gap > 120:  # 2 minutes without data
                issues.append(f"DATA_GAP: {gap:.0f}s since last bar")
                status = "warning"

        # Check for stuck position
        if position != 0 and self._position_entry_time:
            hold_minutes = (datetime.now(timezone.utc) - self._position_entry_time).total_seconds() / 60
            if hold_minutes > self.max_position_age_minutes:
                issues.append(f"STUCK_POSITION: held for {hold_minutes:.0f} minutes")
                status = "critical"

        # Check consecutive errors
        if self._consecutive_errors >= self.max_consecutive_errors:
            issues.append(f"ERROR_THRESHOLD: {self._consecutive_errors} consecutive errors")
            status = "critical"

        # Send alerts
        for issue in issues:
            if self.alert_callback:
                self.alert_callback(status, issue)

        return {
            "status": status,
            "issues": issues,
            "bars_processed": self._bars_processed,
            "bars_since_trade": self._bars_since_trade,
            "trades_today": self._trades_today,
            "errors_today": self._errors_today,
            "consecutive_errors": self._consecutive_errors,
            "uptime_minutes": (datetime.now(timezone.utc) - self._start_time).total_seconds() / 60,
        }


class LiveRunner:
    """
    Production live trading runner.

    Orchestrates:
    - Real-time market data from Tradovate
    - V2 signal/belief/decision engines
    - Order execution via Tradovate API
    - Event publishing to Supabase
    - Health monitoring and kill switch
    """

    def __init__(
        self,
        tradovate_config: Optional[TradovateConfig] = None,
        symbol: str = "MESZ4",
        stream_id: str = "MES_LIVE",
        contracts_path: str = "src/trading_bot/contracts",
        db_path: str = "data/events.sqlite",
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        on_alert: Optional[Callable[[str, str], None]] = None,
    ):
        """
        Initialize live runner.

        Args:
            tradovate_config: Tradovate credentials
            symbol: Symbol to trade (e.g., MESZ4)
            stream_id: Event stream ID for logging
            contracts_path: Path to contract YAML files
            db_path: SQLite database path
            supabase_url: Supabase project URL
            supabase_key: Supabase service key
            on_alert: Callback for health alerts
        """
        self.symbol = symbol
        self.stream_id = stream_id
        self.contracts_path = contracts_path
        self.db_path = db_path

        # State
        self._state = RunnerState.STOPPED
        self._running = False
        self._shutdown_event = threading.Event()

        # Components (initialized on start)
        self._adapter: Optional[TradovateLiveAdapter] = None
        self._data_feed: Optional[TradovateDataFeed] = None
        self._event_store: Optional[EventStore] = None
        self._event_publisher: Optional[EventPublisher] = None
        self._trade_publisher: Optional[TradePublisher] = None

        # Engines
        self._signals: Optional[SignalEngineV2] = None
        self._belief: Optional[BeliefEngineV2] = None
        self._decision: Optional[DecisionEngineV2] = None
        self._state_store: Optional[StateStore] = None

        # Health monitoring
        self._health = HealthCheck(alert_callback=on_alert)

        # Config
        self._tradovate_config = tradovate_config or self._load_config_from_env()
        self._supabase_url = supabase_url or os.environ.get("SUPABASE_URL")
        self._supabase_key = supabase_key or os.environ.get("SUPABASE_KEY")

        # Config hash for event reproducibility
        self._config_hash: Optional[str] = None
        self._data_contract: Optional[Dict] = None
        self._execution_contract: Optional[Dict] = None

    def _load_config_from_env(self) -> TradovateConfig:
        """Load Tradovate config from environment variables."""
        env = os.environ.get("TRADOVATE_ENVIRONMENT", "demo").lower()
        return TradovateConfig(
            username=os.environ.get("TRADOVATE_USERNAME", ""),
            password=os.environ.get("TRADOVATE_PASSWORD", ""),
            environment=TradovateEnvironment(env),
        )

    def _init_engines(self) -> None:
        """Initialize trading engines."""
        self._signals = SignalEngineV2()
        self._belief = BeliefEngineV2()
        self._decision = DecisionEngineV2(contracts_path=self.contracts_path)
        self._state_store = StateStore()

        # Load contracts for DVS/EQS
        try:
            self._data_contract = load_yaml_contract(self.contracts_path, "data_contract.yaml")
        except Exception:
            self._data_contract = {"dvs": {"initial_value": 1.0, "degradation_events": []}}

        try:
            self._execution_contract = load_yaml_contract(self.contracts_path, "execution_contract.yaml")
        except Exception:
            self._execution_contract = {"eqs": {"initial_value": 1.0, "degradation_events": []}}

        # Compute config hash
        cfg_sources = {
            "engine_version": "v2_live",
            "symbol": self.symbol,
            "templates": list(self._decision.templates.keys()),
            "data_contract": self._data_contract,
            "execution_contract": self._execution_contract,
        }
        self._config_hash = sha256_hex(stable_json(cfg_sources))

    def _init_stores(self) -> None:
        """Initialize event stores."""
        # SQLite store (primary)
        self._event_store = EventStore(self.db_path)
        schema_path = Path(__file__).resolve().parent.parent / "log" / "schema.sql"
        if schema_path.exists():
            self._event_store.init_schema(str(schema_path))

        # Supabase publisher (secondary)
        if self._supabase_url and self._supabase_key:
            self._event_publisher = EventPublisher(
                sqlite_path=self.db_path,
                supabase_url=self._supabase_url,
                supabase_key=self._supabase_key,
            )
            self._trade_publisher = TradePublisher(
                supabase_url=self._supabase_url,
                supabase_key=self._supabase_key,
            )

    def start(self) -> bool:
        """
        Start live trading.

        Returns:
            True if started successfully
        """
        if self._state != RunnerState.STOPPED:
            logger.warning(f"Cannot start: current state is {self._state}")
            return False

        self._state = RunnerState.STARTING
        logger.info("Starting live runner...")

        try:
            # Initialize engines
            self._init_engines()
            self._init_stores()

            # Connect to Tradovate
            self._adapter = TradovateLiveAdapter(
                config=self._tradovate_config,
                on_fill=self._on_fill,
                on_error=self._on_adapter_error,
            )

            if not self._adapter.start():
                raise Exception("Tradovate authentication failed")

            # Start data feed
            self._data_feed = TradovateDataFeed(
                access_token=self._adapter._access_token,
                symbol=self.symbol,
                environment=self._tradovate_config.environment.value,
                on_bar=self._on_bar,
                on_error=self._on_feed_error,
            )

            if not self._data_feed.start():
                raise Exception("Data feed start failed")

            # Start event publisher
            if self._event_publisher:
                self._event_publisher.start()

            # Set up signal handlers
            signal.signal(signal.SIGINT, self._handle_shutdown)
            signal.signal(signal.SIGTERM, self._handle_shutdown)

            self._running = True
            self._state = RunnerState.RUNNING
            logger.info("Live runner started successfully")

            return True

        except Exception as e:
            logger.exception("Failed to start live runner")
            self._state = RunnerState.ERROR
            return False

    def stop(self) -> None:
        """Stop live trading gracefully."""
        if self._state != RunnerState.RUNNING:
            return

        self._state = RunnerState.STOPPING
        logger.info("Stopping live runner...")

        self._running = False
        self._shutdown_event.set()

        # Stop components
        if self._data_feed:
            self._data_feed.stop()

        if self._adapter:
            # Cancel all orders and flatten
            self._adapter.cancel_all()
            self._adapter.flatten_positions()
            self._adapter.stop()

        if self._event_publisher:
            self._event_publisher.stop()

        self._state = RunnerState.STOPPED
        logger.info("Live runner stopped")

    def run(self) -> None:
        """
        Main run loop (blocking).

        Call this after start() to run until shutdown.
        """
        logger.info("Entering main run loop")

        while self._running and not self._shutdown_event.is_set():
            try:
                # Health check every minute
                health = self._health.check(
                    position=self._adapter.get_position_snapshot()["position"]
                    if self._adapter else 0
                )

                if health["status"] == "critical":
                    logger.critical(f"Health critical: {health['issues']}")
                    if self._adapter:
                        self._adapter.set_kill_switch(True, "HEALTH_CRITICAL")

                # Reconcile position
                if self._adapter:
                    recon = self._adapter.reconcile_position()
                    if not recon.get("match", True):
                        logger.error(f"Position mismatch: {recon}")

                # Poll for updates if WebSocket not connected
                if self._adapter and not self._adapter._ws_connected:
                    self._adapter.poll_updates()

                time.sleep(5)

            except Exception as e:
                logger.error(f"Run loop error: {e}")
                self._health.record_error(str(e))

        self.stop()

    def _on_bar(self, bar: Bar) -> None:
        """
        Handle completed bar from data feed.

        This is the main trading logic callback.
        """
        try:
            logger.info(f"Bar: {bar.timestamp} O={bar.open} H={bar.high} L={bar.low} C={bar.close} V={bar.volume}")

            # Record bar for health check
            self._health.record_bar()

            # Process through V2 engines
            result = self._process_bar(bar)

            # Log decision
            logger.info(f"Decision: {result.get('action')} - {result.get('reason')}")

        except Exception as e:
            logger.exception("Bar processing error")
            self._health.record_error(str(e))

    def _process_bar(self, bar: Bar) -> Dict[str, Any]:
        """Process a bar through the trading engines."""
        dt = bar.timestamp
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ET)

        # Compute DVS/EQS
        dvs_state = {
            "bar_lag_seconds": 0,
            "missing_fields": 0,
            "gap_detected": False,
        }
        eqs_state = {
            "connection_state": "OK" if self._data_feed.is_connected() else "DEGRADED",
        }
        dvs_val = float(compute_dvs(dvs_state, self._data_contract))
        eqs_val = float(compute_eqs(eqs_state, self._execution_contract))

        # Compute signals
        signal_output = self._signals.compute_signals(
            timestamp=dt,
            open_price=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
            bid=bar.bid or bar.close,
            ask=bar.ask or bar.close,
            dvs=dvs_val,
            eqs=eqs_val,
        )

        # Build signals dict
        signals_dict = {
            "vwap_z": signal_output.vwap_z,
            "atr_14_n": signal_output.atr_14_n,
            "vol_z": signal_output.vol_z,
            "session_phase": signal_output.session_phase,
            "dvs": signal_output.dvs,
            "spread_ticks": float(self._data_feed.get_spread() or 1),
            "slippage_estimate_ticks": 1,
            # ... other signals
        }

        # Compute beliefs
        beliefs = self._belief.compute_beliefs(
            signals=signals_dict,
            session_phase=signal_output.session_phase,
            dvs=dvs_val,
            eqs=eqs_val,
        )

        # Get state
        risk_state = self._state_store.get_risk_state(now=dt)
        equity = Decimal("5000.00")  # TODO: Get from account

        state = {
            "dvs": dvs_val,
            "eqs": eqs_val,
            "position": self._adapter.get_position_snapshot()["position"] if self._adapter else 0,
            "last_price": bar.close,
            "timestamp": dt,
            "equity_usd": equity,
        }

        # Decision
        decision_result = self._decision.decide(
            equity=equity,
            beliefs=beliefs,
            signals=signals_dict,
            state=state,
            risk_state=risk_state,
        )

        # Log events
        decision_dict = {
            "action": decision_result.action,
            "reason": str(decision_result.reason) if decision_result.reason else None,
            "metadata": decision_result.metadata,
        }

        e = Event.make(self.stream_id, dt.isoformat(), "DECISION_1M", decision_dict, self._config_hash)
        self._event_store.append(e)

        # Execute if order intent
        if decision_result.action == "ORDER_INTENT" and decision_result.order_intent:
            self._execute_order(decision_result, bar, dt)

        return decision_dict

    def _execute_order(self, decision_result: Any, bar: Bar, dt: datetime) -> None:
        """Execute order from decision."""
        intent = decision_result.order_intent
        metadata = decision_result.metadata or {}

        # Build bracket prices
        tick_size = 0.25
        direction = intent.get("direction", "LONG")
        side = 1 if direction == "LONG" else -1
        entry_price = float(bar.close)
        stop_ticks = intent.get("stop_ticks", 8)
        target_ticks = intent.get("target_ticks", 12)
        stop_price = entry_price - side * stop_ticks * tick_size
        target_price = entry_price + side * target_ticks * tick_size

        # Build intent wrapper
        class IntentWrapper:
            def __init__(self, d):
                self.__dict__.update(d)
                self.metadata = {
                    "limit_price": entry_price,
                    "instrument": self.symbol if hasattr(self, 'symbol') else "MESZ4",
                    "bracket": {
                        "stop_price": round(stop_price, 2),
                        "target_price": round(target_price, 2),
                    },
                }

        intent_obj = IntentWrapper(intent)
        order_result = self._adapter.place_order(intent_obj, bar.close)

        if order_result.get("order_id"):
            self._health.record_trade()
            self._state_store.record_entry(dt)

            # Update expected position
            contracts = int(intent.get("contracts", 1))
            self._state_store.update_expected_position(contracts * side)

            # Publish to Supabase
            if self._trade_publisher:
                self._trade_publisher.publish_trade({
                    "timestamp": dt.isoformat(),
                    "symbol": self.symbol,
                    "direction": direction,
                    "contracts": contracts,
                    "entry_price": entry_price,
                    "stop_price": stop_price,
                    "target_price": target_price,
                    "template_id": metadata.get("template_id"),
                    "euc_score": metadata.get("euc_score"),
                })

        # Log order event
        oe = Event.make(self.stream_id, dt.isoformat(), "ORDER_EVENT", order_result, self._config_hash)
        self._event_store.append(oe)

    def _on_fill(self, fill: Dict[str, Any]) -> None:
        """Handle fill event from adapter."""
        logger.info(f"Fill: {fill}")

        # Update state store
        if fill.get("position") == 0:
            self._health.record_exit()
            self._state_store.set_expected_position(0)

    def _on_adapter_error(self, error: str) -> None:
        """Handle adapter error."""
        logger.error(f"Adapter error: {error}")
        self._health.record_error(error)

    def _on_feed_error(self, error: str) -> None:
        """Handle data feed error."""
        logger.error(f"Feed error: {error}")
        self._health.record_error(error)

    def _handle_shutdown(self, signum: int, frame: Any) -> None:
        """Handle shutdown signal."""
        logger.info(f"Received signal {signum}, shutting down...")
        self._shutdown_event.set()

    def get_status(self) -> Dict[str, Any]:
        """Get runner status."""
        health = self._health.check(
            position=self._adapter.get_position_snapshot()["position"]
            if self._adapter else 0
        )

        return {
            "state": self._state.value,
            "symbol": self.symbol,
            "stream_id": self.stream_id,
            "data_feed_connected": self._data_feed.is_connected() if self._data_feed else False,
            "adapter_connected": bool(self._adapter and self._adapter._access_token),
            "position": self._adapter.get_position_snapshot() if self._adapter else {},
            "health": health,
            "publisher_stats": self._event_publisher.get_stats() if self._event_publisher else {},
        }


def run_live(
    symbol: str = "MESZ4",
    environment: str = "demo",
) -> None:
    """
    Convenience function to start live trading.

    Args:
        symbol: Symbol to trade
        environment: "demo" or "live"
    """
    # Load credentials from environment
    config = TradovateConfig(
        username=os.environ.get("TRADOVATE_USERNAME", ""),
        password=os.environ.get("TRADOVATE_PASSWORD", ""),
        environment=TradovateEnvironment(environment.lower()),
    )

    if not config.username or not config.password:
        print("Error: Set TRADOVATE_USERNAME and TRADOVATE_PASSWORD environment variables")
        return

    # Alert callback
    def on_alert(level: str, message: str):
        print(f"[{level.upper()}] {message}")
        # TODO: Send to Slack/Discord/SMS

    runner = LiveRunner(
        tradovate_config=config,
        symbol=symbol,
        on_alert=on_alert,
    )

    if runner.start():
        runner.run()
    else:
        print("Failed to start live runner")
