from __future__ import annotations

from typing import Dict, Any
from pathlib import Path
from decimal import Decimal
from datetime import datetime

from trading_bot.engines.signals_v2 import SignalEngineV2, ET
from trading_bot.engines.decision_v2 import DecisionEngineV2
from trading_bot.engines.belief_v2 import BeliefEngineV2
from trading_bot.engines.dvs_eqs import compute_dvs, compute_eqs
from trading_bot.engines.attribution import attribute
from trading_bot.engines.simulator import simulate_fills
from trading_bot.adapters.tradovate import TradovateAdapter
from trading_bot.core.state_store import StateStore
from trading_bot.core.types import Event, stable_json, sha256_hex
from trading_bot.core.config import load_yaml_contract
from trading_bot.log.event_store import EventStore
from trading_bot.log.decision_journal import DecisionJournal, DecisionRecord


class BotRunner:
    """Glue the signal engine, decision engine, adapter, and event store (v2)."""

    def __init__(self, contracts_path: str = "src/trading_bot/contracts", db_path: str = "data/events.sqlite"):
        self.signals = SignalEngineV2()
        self.belief = BeliefEngineV2()
        self.decision = DecisionEngineV2(contracts_path=contracts_path)
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
            "engine_version": "v2",
            "templates": list(self.decision.templates.keys()),
            "tier_constraints": {t.name: tc.allowed_templates for t, tc in self.decision.tier_constraints.items()},
            "risk_model": risk_model,
            "data_contract": data_contract,
            "execution_contract": execution_contract,
            "signal_params": {"tick_size": str(self.signals.tick_size)},
        }
        self.config_hash = sha256_hex(stable_json(cfg_sources))

    def run_once(self, bar: Dict[str, Any], stream_id: str = "MES_RTH") -> Dict[str, Any]:
        """Process a single bar: compute signals (V2), beliefs (V2), decide (V2), and optionally execute."""
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
        dvs_val = float(compute_dvs(dvs_state, self.data_contract))
        eqs_val = float(compute_eqs(eqs_state, self.execution_contract))

        # In SIM mode, assume 1-tick spread if no L1 bid/ask
        bid = Decimal(str(bar.get("bid", float(close) - 0.25)))
        ask = Decimal(str(bar.get("ask", float(close) + 0.25)))

        # V2 Signal Engine: compute all 28 signals
        signal_output = self.signals.compute_signals(
            timestamp=dt,
            open_price=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            bid=bid,
            ask=ask,
            dvs=dvs_val,
            eqs=eqs_val,
        )

        # Convert SignalOutput dataclass to dict for belief engine
        signals_dict = {
            "vwap_z": signal_output.vwap_z,
            "vwap_slope": signal_output.vwap_slope,
            "atr_14_n": signal_output.atr_14_n,
            "range_compression": signal_output.range_compression,
            "hhll_trend_strength": signal_output.hhll_trend_strength,
            "breakout_distance_n": signal_output.breakout_distance_n,
            "rejection_wick_n": signal_output.rejection_wick_n,
            "close_location_value": signal_output.close_location_value,
            "gap_from_prev_close_n": signal_output.gap_from_prev_close_n,
            "distance_from_poc_proxy": signal_output.distance_from_poc_proxy,
            "micro_trend_5": signal_output.micro_trend_5,
            "real_body_impulse_n": signal_output.real_body_impulse_n,
            "vol_z": signal_output.vol_z,
            "vol_slope_20": signal_output.vol_slope_20,
            "effort_vs_result": signal_output.effort_vs_result,
            "range_expansion_on_volume": signal_output.range_expansion_on_volume,
            "climax_bar_flag": signal_output.climax_bar_flag,
            "quiet_bar_flag": signal_output.quiet_bar_flag,
            "consecutive_high_vol_bars": signal_output.consecutive_high_vol_bars,
            "participation_expansion_index": signal_output.participation_expansion_index,
            "session_phase": signal_output.session_phase,
            "opening_range_break": signal_output.opening_range_break,
            "lunch_void_gate": signal_output.lunch_void_gate,
            "close_magnet_index": signal_output.close_magnet_index,
            "spread_proxy_tickiness": signal_output.spread_proxy_tickiness,
            "slippage_risk_proxy": signal_output.slippage_risk_proxy,
            "friction_regime_index": signal_output.friction_regime_index,
            "dvs": signal_output.dvs,
            # Legacy compat for adapter
            "spread_ticks": 1,
            "slippage_estimate_ticks": 1,
        }

        # V2 Belief Engine: compute constraint likelihoods
        beliefs = self.belief.compute_beliefs(
            signals=signals_dict,
            session_phase=signal_output.session_phase,
            dvs=dvs_val,
            eqs=eqs_val,
        )

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

        # V2 Decision Engine: decide with capital tier gates + EUC scoring
        equity = state.get("equity_usd", Decimal("1000.00"))
        decision_result = self.decision.decide(
            equity=equity,
            beliefs=beliefs,
            signals=signals_dict,
            state=state,
            risk_state=risk_state,
        )

        # Convert beliefs to serializable format for event logging
        beliefs_payload = {
            cid: {
                "evidence": b.evidence,
                "likelihood": b.likelihood,
                "applicability": b.applicability,
                "effective_likelihood": b.effective_likelihood,
                "stability": b.stability,
            }
            for cid, b in beliefs.items()
        }

        # Convert decision result to dict for event logging
        decision_dict = {
            "action": decision_result.action,
            "reason": str(decision_result.reason) if decision_result.reason else None,
            "metadata": decision_result.metadata,
            "order_intent": decision_result.order_intent,
        }

        # Log beliefs and decision
        b_event = Event.make(stream_id, dt.isoformat(), "BELIEFS_1M", beliefs_payload, self.config_hash)
        self.events.append(b_event)
        e = Event.make(stream_id, dt.isoformat(), "DECISION_1M", decision_dict, self.config_hash)
        self.events.append(e)

        # Decision Journal: emit exactly once per cycle
        journal = DecisionJournal(self.events, stream_id=stream_id, config_hash=self.config_hash)
        setup_scores = {cid: b.effective_likelihood for cid, b in beliefs.items()}

        context = {
            "dvs": dvs_val,
            "eqs": eqs_val,
            "session_phase": signal_output.session_phase,
            "spread_ticks": 1,
        }

        if decision_result.action == "ORDER_INTENT":
            # Trade intent summary
            metadata = decision_result.metadata or {}
            setup_id = metadata.get("template_id", "UNKNOWN")
            euc_score = metadata.get("euc_score")
            pe = DecisionJournal.summarize_trade("ENTER", setup_id, euc_score, context)
            record = DecisionRecord(
                time=dt.isoformat(),
                instrument=stream_id,
                action="ENTER",
                setup_scores=setup_scores,
                euc_score=euc_score,
                reasons={"reason_code": "ENTER", "details": metadata},
                plain_english=pe,
                context=context,
            )
            journal.log(record)
        else:
            # No-trade summary
            reason_str = str(decision_result.reason) if decision_result.reason else "UNKNOWN"
            reasons = {"reason_code": reason_str, "details": decision_result.metadata or {}}
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
        if decision_result.action == "ORDER_INTENT" and decision_result.order_intent:
            intent = decision_result.order_intent
            # Compute bracket prices from stop/target ticks
            tick_size = float(self.signals.tick_size)
            direction = intent.get("direction", "LONG")
            side = 1 if direction == "LONG" else -1
            entry_price = float(close)
            stop_ticks = intent.get("stop_ticks", 8)
            target_ticks = intent.get("target_ticks", 12)
            stop_price = entry_price - side * stop_ticks * tick_size
            target_price = entry_price + side * target_ticks * tick_size

            # Wrap intent dict to have attribute access for adapter
            class IntentWrapper:
                def __init__(self, d):
                    self.__dict__.update(d)
                    self.metadata = d.get("metadata", {})
                    self.metadata["limit_price"] = entry_price
                    self.metadata["bracket"] = {
                        "stop_price": round(stop_price, 2),
                        "target_price": round(target_price, 2),
                        "target_qty": max(1, int(d.get("contracts", 1))),
                    }

            intent_obj = IntentWrapper(intent)
            order_res = self.adapter.place_order(intent_obj, close)
            self.state_store.record_entry(dt)

            # Update expected position based on intent
            contracts = int(intent.get("contracts", 1))
            delta = contracts * side
            self.state_store.update_expected_position(delta)

            oe = Event.make(stream_id, dt.isoformat(), "ORDER_EVENT", order_res, self.config_hash)
            self.events.append(oe)

            # Only simulate fills and attribute if order accepted/filled
            if order_res.get("status") in ("FILLED", "PARTIALLY_FILLED", "ACCEPTED", "WORKING"):
                fill_payload = simulate_fills(
                    {"direction": direction, "contracts": contracts},
                    {"last_price": float(close), "spread_ticks": signals_dict["spread_ticks"]},
                    {"tick_size": tick_size, "slippage_ticks": signals_dict["slippage_estimate_ticks"], "spread_to_slippage_ratio": 0.5},
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
                    "eqs": eqs_val,
                    "dvs": dvs_val,
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

        return decision_dict
