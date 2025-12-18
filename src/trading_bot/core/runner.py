from __future__ import annotations

from typing import Dict, Any
from pathlib import Path
from decimal import Decimal
from datetime import datetime

from trading_bot.engines.signals import SignalEngine, ET
from trading_bot.engines.decision import DecisionEngine
from trading_bot.engines.dvs_eqs import compute_dvs, compute_eqs
from trading_bot.engines.belief import update_beliefs
from trading_bot.engines.attribution import attribute
from trading_bot.engines.simulator import simulate_fills
from trading_bot.adapters.tradovate import TradovateAdapter
from trading_bot.core.state_store import StateStore
from trading_bot.core.types import Event, stable_json, sha256_hex
from trading_bot.core.config import load_yaml_contract
from trading_bot.log.event_store import EventStore
from trading_bot.log.decision_journal import DecisionJournal, DecisionRecord


class BotRunner:
    """Glue the signal engine, decision engine, adapter, and event store (v1)."""

    def __init__(self, contracts_path: str = "src/trading_bot/contracts", db_path: str = "data/events.sqlite"):
        self.signals = SignalEngine()
        self.decision = DecisionEngine(contracts_path=contracts_path)
        self.adapter = TradovateAdapter(mode="SIMULATED")
        self.state_store = StateStore()
        self.events = EventStore(db_path)
        # Ensure event store schema exists
        schema_path = Path(__file__).resolve().parent.parent / "log" / "schema.sql"
        if schema_path.exists():
            self.events.init_schema(str(schema_path))
        # Derive config hash from contracts + signal params for reproducibility
        self.contracts_path = contracts_path
        try:
            risk_model = load_yaml_contract(contracts_path, "risk_model.yaml")
        except Exception:
            risk_model = {"missing": True}
        try:
            data_contract = load_yaml_contract(contracts_path, "data_contract.yaml")
        except Exception:
            data_contract = {"dvs": {"initial_value": 1.0, "degradation_events": []}}
        try:
            execution_contract = load_yaml_contract(contracts_path, "execution_contract.yaml")
        except Exception:
            execution_contract = {"eqs": {"initial_value": 1.0, "degradation_events": []}}
        self.data_contract = data_contract
        self.execution_contract = execution_contract

        cfg_sources = {
            "constitution": self.decision.constitution,
            "session": self.decision.session,
            "strategy_templates": self.decision.strategy_templates,
            "risk_model": risk_model,
            "data_contract": data_contract,
            "execution_contract": execution_contract,
            "signal_params": {"tick_size": str(self.signals.tick_size)},
        }
        self.config_hash = sha256_hex(stable_json(cfg_sources))
        self._belief_state: Dict[str, Any] = {}

    def run_once(self, bar: Dict[str, Any], stream_id: str = "MES_RTH") -> Dict[str, Any]:
        """Process a single bar: compute signals, decide, and optionally execute."""
        ts = bar.get("ts")
        # Assume ts is ISO string; convert to datetime ET
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ET)

        high = Decimal(str(bar["h"]))
        low = Decimal(str(bar["l"]))
        close = Decimal(str(bar["c"]))
        volume = int(bar.get("v", 0))

        vwap = self.signals.update_vwap(dt, high, low, close, volume)
        atrs = self.signals.update_atrs(high, low, close)
        phase = self.signals.get_session_phase(dt)

        vwap_distance_pct = None
        if vwap is not None and vwap != 0:
            vwap_distance_pct = float(((close - vwap) / vwap) * Decimal("100"))

        signals = {
            "session_phase_code": phase.phase_code,
            "vwap": vwap,
            "atr14": atrs["atr14"],
            "atr30": atrs["atr30"],
            "tr": atrs["tr"],
            "vwap_distance_pct": vwap_distance_pct,
            # In SIM mode, assume a 1-tick spread if no L1
            "spread_ticks": 1,
            "slippage_estimate_ticks": 1,
        }

        # DVS/EQS computation using contracts and current metrics
        dvs_state = {
            "bar_lag_seconds": bar.get("lag_seconds"),
            "missing_fields": 0,
            "gap_detected": False,
            "outlier_score": bar.get("outlier_score"),
            "price_jump_pct": bar.get("price_jump_pct"),
            "volume_spike_ratio": bar.get("volume_spike_ratio"),
        }
        eqs_state = {
            "fill_price": None,
            "limit_price": None,
            "expected_slippage": bar.get("expected_slippage"),
            "order_state": "IDLE",
            "connection_state": "OK",
        }
        dvs_val = Decimal(str(compute_dvs(dvs_state, self.data_contract)))
        eqs_val = Decimal(str(compute_eqs(eqs_state, self.execution_contract)))

        # Build state snapshot
        risk_state = self.state_store.get_risk_state(now=dt)
        state = {
            "dvs": dvs_val,
            "eqs": eqs_val,
            "position": self.adapter.get_position_snapshot()["position"],
            "last_price": close,
            "timestamp": dt,
            "equity_usd": Decimal("1000.00"),
        }

        # Belief update
        belief_cfg = self._belief_state.get("cfg") or {
            "constraints": [
                {"id": "F1", "weights": {"vwap_distance_pct": 1.0}, "decay_lambda": 0.1},
            ],
            "signal_norms": {"vwap_distance_pct": {"min": -2.0, "max": 2.0}},
            "stability": {"alpha": 0.2},
        }
        beliefs = update_beliefs(signals, self._belief_state.get("beliefs_state", {}), belief_cfg)
        self._belief_state["beliefs_state"] = beliefs

        decision = self.decision.decide(signals, state, risk_state)

        # Log beliefs and decision
        b_event = Event.make(stream_id, dt.isoformat(), "BELIEFS_1M", beliefs, self.config_hash)
        self.events.append(b_event)
        e = Event.make(stream_id, dt.isoformat(), "DECISION_1M", decision, self.config_hash)
        self.events.append(e)

        # Decision Journal: emit exactly once per cycle
        journal = DecisionJournal(self.events, stream_id=stream_id, config_hash=self.config_hash)
        setup_scores = {}
        try:
            if isinstance(beliefs, dict) and isinstance(beliefs.get("beliefs"), dict):
                setup_scores = {k: float(v) for k, v in beliefs["beliefs"].items()}
        except Exception:
            setup_scores = {}

        context = {
            "dvs": float(state.get("dvs", 0) or 0),
            "eqs": float(state.get("eqs", 0) or 0),
            "session_phase": signals.get("session_phase_code"),
            "spread_ticks": signals.get("spread_ticks"),
        }

        if decision.get("action") == "ORDER_INTENT":
            # Trade intent summary
            metadata = decision.get("metadata", {}) or {}
            setup_id = metadata.get("strategy_id", "UNKNOWN")
            pe = DecisionJournal.summarize_trade("ENTER", setup_id, None, context)
            record = DecisionRecord(
                time=dt.isoformat(),
                instrument=stream_id,
                action="ENTER",
                setup_scores=setup_scores,
                euc_score=None,
                reasons={"reason_code": "ENTER", "details": metadata},
                plain_english=pe,
                context=context,
            )
            journal.log(record)
        else:
            # No-trade summary
            reason = decision.get("reason")
            reasons = {"reason_code": str(reason), "details": decision.get("metadata", {})}
            pe = DecisionJournal.summarize_no_trade(setup_scores, reasons, context)
            record = DecisionRecord(
                time=dt.isoformat(),
                instrument=stream_id,
                action="SKIP",
                setup_scores=setup_scores,
                euc_score=None,
                reasons=reasons,
                plain_english=pe,
                context=context,
            )
            journal.log(record)

        # If order intent, simulate placement and record entry
        if decision["action"] == "ORDER_INTENT":
            intent = decision["intent"]
            # Enforce limit-only + bracket in SIM to match constitution
            try:
                intent.entry_type = "LIMIT"
            except Exception:
                pass
            # Compute bracket prices from stop/target ticks
            try:
                tick_size = float(self.signals.tick_size)
            except Exception:
                tick_size = 0.25
            side = 1 if getattr(intent, "direction", "LONG") == "LONG" else -1
            entry_price = close
            stop_price = float(entry_price) - side * float(intent.stop_ticks) * tick_size
            target_price = float(entry_price) + side * float(intent.target_ticks) * tick_size
            # Inject bracket + limit price into metadata
            meta = getattr(intent, "metadata", {}) or {}
            meta["limit_price"] = float(entry_price)
            meta["bracket"] = {
                "stop_price": round(stop_price, 2),
                "target_price": round(target_price, 2),
                "target_qty": max(1, int(getattr(intent, "contracts", 1) or 1) - 0),
            }
            intent.metadata = meta

            order_res = self.adapter.place_order(intent, close)
            self.state_store.record_entry(dt)
            # Update expected position based on intent
            try:
                delta = int(intent.contracts) * (1 if getattr(intent, "direction", "LONG") == "LONG" else -1)
                self.state_store.update_expected_position(delta)
            except Exception:
                pass
            oe = Event.make(stream_id, dt.isoformat(), "ORDER_EVENT", order_res, self.config_hash)
            self.events.append(oe)

            # Only simulate fills and attribute if order accepted/filled
            if order_res.get("status") in ("FILLED", "PARTIALLY_FILLED", "ACCEPTED", "WORKING"):
                fill_payload = simulate_fills(
                    {
                        "direction": intent.direction,
                        "contracts": intent.contracts,
                    },
                    {"last_price": float(close), "spread_ticks": signals["spread_ticks"]},
                    {"tick_size": float(self.signals.tick_size), "slippage_ticks": signals["slippage_estimate_ticks"], "spread_to_slippage_ratio": 0.5},
                )
                fe = Event.make(stream_id, dt.isoformat(), "FILL_EVENT", fill_payload["payload"], self.config_hash)
                self.events.append(fe)

                trade_record = {
                    "entry_price": float(close),
                    "exit_price": float(fill_payload["payload"].get("fill_price", close)),
                    "pnl_usd": 0.0,
                    "duration_seconds": 0,
                    "slippage_ticks": fill_payload["payload"].get("slippage_ticks"),
                    "spread_ticks": fill_payload["payload"].get("spread_ticks"),
                    "eqs": float(eqs_val),
                    "dvs": float(dvs_val),
                }
                attr = attribute(trade_record, {"rules": [], "default": {"id": "A0_UNCLASSIFIED", "process_score": 0.5, "outcome_score": 0.5}})
                attr_event = Event.make(stream_id, dt.isoformat(), "ATTRIBUTION", attr, self.config_hash)
                self.events.append(attr_event)

        # Reconciliation + TTL enforcement (lightweight per-cycle check)
        try:
            expected_pos = self.state_store.get_expected_position()
            actual_snap = self.adapter.get_position_snapshot()
            actual_pos = int(actual_snap.get("position", 0))
            recon_payload = {"expected_position": expected_pos, "actual_position": actual_pos, "actions": []}

            if expected_pos != actual_pos:
                # Trigger kill per constitution (fail-safe)
                self.adapter.set_kill_switch(True)
                try:
                    self.adapter.flatten_positions()
                finally:
                    self.state_store.set_expected_position(0)
                recon_payload["kill_switch"] = True
                recon_payload["kill_reason"] = "ORDER_STATE_DESYNC"

            # TTL cancel loop (only orders not filled)
            ttl_seconds = int(bar.get("order_ttl_seconds", 0) or 0) or 90
            open_orders = self.adapter.get_open_orders()
            for oid, od in open_orders.items():
                st = od.get("status")
                if st in ("NEW", "WORKING", "ACCEPTED"):
                    try:
                        created_at = datetime.fromisoformat(str(od.get("created_at")))
                    except Exception:
                        created_at = dt
                    age = (dt - created_at).total_seconds()
                    if age > ttl_seconds:
                        if self.adapter.cancel_order(oid):
                            recon_payload["actions"].append({"action": "CANCEL", "order_id": oid, "age_seconds": age})

            re = Event.make(stream_id, dt.isoformat(), "SYSTEM_EVENT", {"reconciliation": recon_payload}, self.config_hash)
            self.events.append(re)
        except Exception:
            # Do not fail the loop on recon errors; emit minimal event
            re = Event.make(stream_id, dt.isoformat(), "SYSTEM_EVENT", {"reconciliation": {"error": True}}, self.config_hash)
            self.events.append(re)

        return decision
