from __future__ import annotations

from typing import Dict, Any
from pathlib import Path
from decimal import Decimal
from datetime import datetime

from dataclasses import asdict
from enum import Enum

from trading_bot.engines.signals_v2 import SignalEngineV2 as SignalEngine, ET
from trading_bot.engines.decision_v2 import DecisionEngineV2 as DecisionEngine
from trading_bot.engines.belief_v2 import BeliefEngineV2
from trading_bot.engines.dvs_eqs import compute_dvs, compute_eqs
from trading_bot.engines.attribution import attribute
from trading_bot.engines.simulator import simulate_fills
from trading_bot.core.adapter_factory import create_adapter
from trading_bot.core.state_store import StateStore
from trading_bot.core.types import Event, stable_json, sha256_hex
from trading_bot.core.config import load_yaml_contract
from trading_bot.log.event_store import EventStore
from trading_bot.log.decision_journal import DecisionJournal, DecisionRecord


class BotRunner:
    """Glue the signal engine, decision engine, adapter, and event store (v1)."""

    def __init__(self, contracts_path: str = "src/trading_bot/contracts", db_path: str = "data/events.sqlite", adapter: str = "tradovate", fill_mode: str = "IMMEDIATE", adapter_kwargs: Dict[str, Any] | None = None):
        self.signals = SignalEngine()
        self.beliefs = BeliefEngineV2()
        self.decision = DecisionEngine(contracts_path=contracts_path)
        akwargs = adapter_kwargs or {}
        if adapter.lower() in ("tradovate", "tv", "sim"):
            akwargs = {**akwargs, "fill_mode": fill_mode}
        self.adapter = create_adapter(adapter, **akwargs)
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

        # Normalize decision engine config for hashing (avoid missing attrs on V2)
        tier_cfg = {}
        try:
            for k, v in getattr(self.decision, "tier_constraints", {}).items():
                asd = asdict(v)
                for kk, vv in list(asd.items()):
                    if isinstance(vv, Decimal):
                        asd[kk] = str(vv)
                    elif isinstance(vv, Enum):
                        asd[kk] = vv.name
                tier_cfg[getattr(k, "name", str(k))] = asd
        except Exception:
            tier_cfg = {}

        cfg_sources = {
            "templates": getattr(self.decision, "templates", {}),
            "tier_constraints": tier_cfg,
            "euc_params": getattr(self.decision, "euc_params", {}),
            "risk_model": risk_model,
            "data_contract": data_contract,
            "execution_contract": execution_contract,
            "signal_params": {"tick_size": str(self.signals.tick_size)},
        }
        self.config_hash = sha256_hex(stable_json(cfg_sources))
        self._belief_state: Dict[str, Any] = {}

    def run_once(self, bar: Dict[str, Any], stream_id: str = "MES_RTH") -> Dict[str, Any]:
        """Process a single bar with V2 engines: signals → beliefs → decision → execution."""
        ts = bar.get("ts")
        # Assume ts is ISO string; convert to datetime ET
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ET)

        open_price = Decimal(str(bar.get("o", bar["c"])))
        high = Decimal(str(bar["h"]))
        low = Decimal(str(bar["l"]))
        close = Decimal(str(bar["c"]))
        volume = int(bar.get("v", 0))

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

        # --- V2 signals ---
        # Approximate L1 if absent: 1-tick spread around close
        half_tick = self.signals.tick_size / Decimal("2")
        bid = Decimal(str(bar.get("bid", close - half_tick)))
        ask = Decimal(str(bar.get("ask", close + half_tick)))

        signal_out = self.signals.compute_signals(
            timestamp=dt,
            open_price=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            bid=bid,
            ask=ask,
            dvs=float(dvs_val),
            eqs=float(eqs_val),
        )

        # Make signals JSON-safe
        signal_dict = asdict(signal_out)
        signal_dict["timestamp"] = dt.isoformat()
        # Reliability is a nested dataclass; leave as dict from asdict

        # --- Beliefs ---
        beliefs = self.beliefs.compute_beliefs(
            signals=signal_dict,
            session_phase=signal_dict.get("session_phase", 0),
            dvs=float(dvs_val),
            eqs=float(eqs_val),
        )
        belief_payload = {cid: asdict(b) for cid, b in beliefs.items()}

        # --- Decision ---
        decision_result = self.decision.decide(
            equity=state["equity_usd"],
            beliefs=beliefs,
            signals=signal_dict,
            state=state,
            risk_state=risk_state,
        )

        # Log beliefs and decision
        b_event = Event.make(stream_id, dt.isoformat(), "BELIEFS_1M", belief_payload, self.config_hash)
        self.events.append(b_event)
        decision_payload = {
            "action": decision_result.action,
            "reason": decision_result.reason.name if hasattr(decision_result.reason, "name") else decision_result.reason,
            "order_intent": decision_result.order_intent,
            "metadata": decision_result.metadata,
            "timestamp": decision_result.timestamp.isoformat(),
        }
        e = Event.make(stream_id, dt.isoformat(), "DECISION_1M", decision_payload, self.config_hash)
        self.events.append(e)

        # Decision Journal: emit exactly once per cycle
        journal = DecisionJournal(self.events, stream_id=stream_id, config_hash=self.config_hash)
        # Use effective likelihoods as setup scores
        setup_scores = {cid: float(b.effective_likelihood) for cid, b in beliefs.items()}

        context = {
            "dvs": float(state.get("dvs", 0) or 0),
            "eqs": float(state.get("eqs", 0) or 0),
            "session_phase": signal_dict.get("session_phase"),
            "spread_ticks": signal_dict.get("spread_proxy_tickiness"),
        }

        if decision_result.action == "ORDER_INTENT":
            metadata = decision_result.metadata or {}
            setup_id = metadata.get("template_id", "UNKNOWN")
            pe = DecisionJournal.summarize_trade("ENTER", setup_id, metadata.get("euc_score"), context)
            record = DecisionRecord(
                time=dt.isoformat(),
                instrument=stream_id,
                action="ENTER",
                setup_scores=setup_scores,
                euc_score=metadata.get("euc_score"),
                reasons={"reason_code": "ENTER", "details": metadata},
                plain_english=pe,
                context=context,
            )
            journal.log(record)
        else:
            reason = decision_result.reason
            reason_code = reason.name if hasattr(reason, "name") else str(reason)
            reasons = {"reason_code": reason_code, "details": decision_result.metadata or {}}
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

        # If order intent, place and record entry
        if decision_result.action == "ORDER_INTENT":
            intent = decision_result.order_intent or {}
            # Enforce limit-only + bracket
            intent["entry_type"] = "LIMIT"
            tick_size = float(self.signals.tick_size)
            side = 1 if intent.get("direction", "LONG") == "LONG" else -1
            entry_price = float(close)
            stop_ticks = int(intent.get("stop_ticks", 0) or 0)
            target_ticks = int(intent.get("target_ticks", 0) or 0)
            stop_price = entry_price - side * stop_ticks * tick_size
            target_price = entry_price + side * target_ticks * tick_size
            meta = intent.get("metadata", {}) or {}
            meta.update(
                {
                    "limit_price": entry_price,
                    "bracket": {
                        "stop_price": round(stop_price, 2),
                        "target_price": round(target_price, 2),
                        "target_qty": max(1, int(intent.get("contracts", 1) or 1)),
                    },
                }
            )
            intent["metadata"] = meta

            class _IntentObj:
                def __init__(self, d: Dict[str, Any]):
                    for k, v in d.items():
                        setattr(self, k, v)

            intent_obj = _IntentObj(intent)
            order_res = self.adapter.place_order(intent_obj, close)
            self.state_store.record_entry(dt)
            try:
                filled_delta = int(order_res.get("filled_delta", 0) or 0)
                if filled_delta:
                    self.state_store.update_expected_position(filled_delta)
            except Exception:
                pass
            oe = Event.make(stream_id, dt.isoformat(), "ORDER_EVENT", order_res, self.config_hash)
            self.events.append(oe)
            # no simulated fills here; adapter may emit fills via on_cycle()/pop_events

        # Adapter per-cycle processing (fill progression for SIM)
        try:
            recon_interval = int(self.execution_contract.get("order_lifecycle", {}).get("reconciliation_interval_bars", 1))
        except Exception:
            recon_interval = 1
        try:
            self.adapter.on_cycle(dt)
            for evt in getattr(self.adapter, "pop_events", lambda: [])():
                if evt.get("type") == "FILL":
                    fe = Event.make(stream_id, dt.isoformat(), "FILL_EVENT", evt, self.config_hash)
                    self.events.append(fe)
                    # Update expected position on fills
                    try:
                        filled_qty = int(evt.get("filled_qty", 0) or 0)
                        # direction not present in evt; infer from position delta is tricky; skip for now
                        # Runner keeps expected position conservative unless immediate fill returned earlier
                    except Exception:
                        pass
                    # Emit basic attribution stub (placeholder)
                    trade_record = {
                        "entry_price": float(close),
                        "exit_price": float(evt.get("fill_price", float(close))),
                        "pnl_usd": 0.0,
                        "duration_seconds": 0,
                        "slippage_ticks": signal_dict.get("slippage_risk_proxy"),
                        "spread_ticks": signal_dict.get("spread_proxy_tickiness"),
                        "eqs": float(eqs_val),
                        "dvs": float(dvs_val),
                    }
                    attr = attribute(trade_record, {"rules": [], "default": {"id": "A0_UNCLASSIFIED", "process_score": 0.5, "outcome_score": 0.5}})
                    attr_event = Event.make(stream_id, dt.isoformat(), "ATTRIBUTION", attr, self.config_hash)
                    self.events.append(attr_event)
        except Exception:
            pass

        # Reconciliation + TTL enforcement with pacing
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

            # TTL cancel loop (only orders not filled) — configured via execution_contract
            ttl_seconds = 90
            try:
                ttl_seconds = int(self.execution_contract.get("order_lifecycle", {}).get("ttl_seconds", ttl_seconds))
            except Exception:
                ttl_seconds = 90
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

            # Emit reconciliation per configured interval
            if not hasattr(self, "_recon_bar_counter"):
                self._recon_bar_counter = 0
            self._recon_bar_counter += 1
            if self._recon_bar_counter % max(1, recon_interval) == 0:
                re = Event.make(stream_id, dt.isoformat(), "RECONCILIATION", recon_payload, self.config_hash)
                self.events.append(re)
        except Exception:
            # Do not fail the loop on recon errors; emit minimal event
            if not hasattr(self, "_recon_bar_counter"):
                self._recon_bar_counter = 0
            self._recon_bar_counter += 1
            if self._recon_bar_counter % max(1, recon_interval) == 0:
                re = Event.make(stream_id, dt.isoformat(), "RECONCILIATION", {"error": True}, self.config_hash)
                self.events.append(re)

        return decision_payload
