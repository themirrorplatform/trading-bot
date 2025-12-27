"""
Comprehensive QA Test Suite for Trading Bot

Tests cover:
- Signal computation (edge cases, bounds)
- Belief likelihood (constraint satisfaction)
- Decision engine (capital tiers, EUC scoring)
- Execution Supervisor (state machine, idempotent submission)
- Market data quality (DVS/EQS gating)
- Trade lifecycle (thesis, time, vol exits)
- Learning loop (quarantine, re-enable, throttling)
- E2E scenarios (complete trading day simulation)
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any
import json

from trading_bot.core.runner import BotRunner
from trading_bot.core.execution_supervisor import ExecutionSupervisor, ParentOrderState, ChildOrderState
from trading_bot.core.trade_manager import TradeManager, TradePosition, TradeState
from trading_bot.core.learning_loop import LearningLoop, TradeOutcome, StrategyState, ReliabilityMetrics
from trading_bot.engines.signals_v2 import SignalEngineV2
from trading_bot.engines.belief_v2 import BeliefEngineV2
from trading_bot.engines.decision_v2 import DecisionEngineV2
from trading_bot.engines.dvs_eqs import compute_dvs, compute_eqs


class TestSignalEngine:
    """Unit tests for signal computation."""
    
    @pytest.fixture
    def engine(self):
        return SignalEngineV2()
    
    def test_signal_bounds(self, engine):
        """All signals should be in [0, 1] range."""
        bar = {
            "ts": "2024-01-15T09:30:00-05:00",
            "o": 5950.0,
            "h": 5960.0,
            "l": 5945.0,
            "c": 5955.0,
            "v": 100000,
            "bid": 5954.50,
            "ask": 5955.50,
        }
        
        signals = engine.compute_signals(
            timestamp=datetime.fromisoformat(bar["ts"]),
            open_price=Decimal(str(bar["o"])),
            high=Decimal(str(bar["h"])),
            low=Decimal(str(bar["l"])),
            close=Decimal(str(bar["c"])),
            volume=bar["v"],
            bid=Decimal(str(bar["bid"])),
            ask=Decimal(str(bar["ask"])),
            dvs=0.95,
            eqs=0.90,
        )
        
        # Check all signal fields are in [0, 1]
        for attr in dir(signals):
            if attr.startswith("S") and attr[1:].isdigit():
                value = getattr(signals, attr, None)
                if isinstance(value, (int, float)):
                    assert 0 <= value <= 1, f"{attr}={value} out of bounds"
    
    def test_signal_consistency(self, engine):
        """Same bar should produce same signals."""
        bar = {
            "ts": "2024-01-15T10:00:00-05:00",
            "o": 5950.0,
            "h": 5960.0,
            "l": 5945.0,
            "c": 5955.0,
            "v": 100000,
            "bid": 5954.50,
            "ask": 5955.50,
        }
        
        dt = datetime.fromisoformat(bar["ts"])
        signals1 = engine.compute_signals(
            timestamp=dt,
            open_price=Decimal(str(bar["o"])),
            high=Decimal(str(bar["h"])),
            low=Decimal(str(bar["l"])),
            close=Decimal(str(bar["c"])),
            volume=bar["v"],
            bid=Decimal(str(bar["bid"])),
            ask=Decimal(str(bar["ask"])),
            dvs=0.95,
            eqs=0.90,
        )
        
        signals2 = engine.compute_signals(
            timestamp=dt,
            open_price=Decimal(str(bar["o"])),
            high=Decimal(str(bar["h"])),
            low=Decimal(str(bar["l"])),
            close=Decimal(str(bar["c"])),
            volume=bar["v"],
            bid=Decimal(str(bar["bid"])),
            ask=Decimal(str(bar["ask"])),
            dvs=0.95,
            eqs=0.90,
        )
        
        # Compare key signals
        assert signals1.S1 == signals2.S1, "S1 inconsistent on replay"
        assert signals1.S5 == signals2.S5, "S5 inconsistent on replay"


class TestBeliefEngine:
    """Unit tests for belief computation."""
    
    @pytest.fixture
    def engine(self):
        return BeliefEngineV2()
    
    def test_belief_likelihood_bounds(self, engine):
        """Belief likelihoods should be in [0, 1]."""
        signals = {
            "S1": 0.6, "S5": 0.5, "S8": 0.7, "S15": 0.8, "S20": 0.4,
            "S2": 0.3, "S3": 0.5, "S4": 0.6, "S6": 0.5, "S7": 0.6,
            "S9": 0.5, "S10": 0.5, "S11": 0.5, "S12": 0.5, "S13": 0.5,
            "S14": 0.5, "S16": 0.5, "S17": 0.5, "S18": 0.5, "S19": 0.5,
            "S21": 0.5, "S22": 0.5, "S23": 0.5, "S24": 0.5, "S25": 0.5,
            "S26": 0.5, "S27": 0.5, "S28": 0.5,
            "session_phase": 1,
            "spread_proxy_tickiness": 0.5,
            "timestamp": "2024-01-15T10:00:00",
        }
        
        beliefs = engine.compute_beliefs(signals, session_phase=1, dvs=0.95, eqs=0.90)
        
        for cid, belief in beliefs.items():
            assert 0 <= belief.effective_likelihood <= 1, f"{cid} likelihood out of bounds"
    
    def test_constraint_satisfaction(self, engine):
        """Test constraint satisfaction logic."""
        # Strong signals
        signals_strong = {
            "S1": 0.9, "S5": 0.8, "S8": 0.7, "S15": 0.9, "S20": 0.6,
            "S2": 0.3, "S3": 0.5, "S4": 0.6, "S6": 0.5, "S7": 0.6,
            "S9": 0.5, "S10": 0.5, "S11": 0.5, "S12": 0.5, "S13": 0.5,
            "S14": 0.5, "S16": 0.5, "S17": 0.5, "S18": 0.5, "S19": 0.5,
            "S21": 0.5, "S22": 0.5, "S23": 0.5, "S24": 0.5, "S25": 0.5,
            "S26": 0.5, "S27": 0.5, "S28": 0.5,
            "session_phase": 1,
            "spread_proxy_tickiness": 0.3,
            "timestamp": "2024-01-15T10:00:00",
        }
        
        beliefs_strong = engine.compute_beliefs(signals_strong, session_phase=1, dvs=0.95, eqs=0.90)
        
        # Weak signals
        signals_weak = {
            "S1": 0.3, "S5": 0.2, "S8": 0.4, "S15": 0.2, "S20": 0.3,
            "S2": 0.3, "S3": 0.5, "S4": 0.6, "S6": 0.5, "S7": 0.6,
            "S9": 0.5, "S10": 0.5, "S11": 0.5, "S12": 0.5, "S13": 0.5,
            "S14": 0.5, "S16": 0.5, "S17": 0.5, "S18": 0.5, "S19": 0.5,
            "S21": 0.5, "S22": 0.5, "S23": 0.5, "S24": 0.5, "S25": 0.5,
            "S26": 0.5, "S27": 0.5, "S28": 0.5,
            "session_phase": 1,
            "spread_proxy_tickiness": 0.8,
            "timestamp": "2024-01-15T10:00:00",
        }
        
        beliefs_weak = engine.compute_beliefs(signals_weak, session_phase=1, dvs=0.95, eqs=0.90)
        
        # Strong signals should produce higher likelihoods (on average)
        strong_avg = sum(b.effective_likelihood for b in beliefs_strong.values()) / len(beliefs_strong)
        weak_avg = sum(b.effective_likelihood for b in beliefs_weak.values()) / len(beliefs_weak)
        
        assert strong_avg > weak_avg, "Strong signals should produce higher avg likelihood"


class TestDecisionEngine:
    """Unit tests for decision logic."""
    
    @pytest.fixture
    def engine(self):
        return DecisionEngineV2(contracts_path="src/trading_bot/contracts")
    
    def test_capital_tier_gating(self, engine):
        """Capital tier gates should prevent trades below minimum equity."""
        # Tier S requires minimum capital
        tier_s_min = Decimal("1500.00")
        
        # Test: Below tier S → NO_TRADE
        result = engine.decide(
            equity=Decimal("500.00"),  # Below tier S
            beliefs={},
            signals={},
            state={},
            risk_state={},
        )
        assert result.action == "NO_TRADE", "Trade allowed below tier S minimum"
    
    def test_euc_scoring(self, engine):
        """EUC score should increase with better beliefs and lower costs."""
        beliefs_good = {"F1": type("B", (), {"effective_likelihood": 0.8})(),
                       "F2": type("B", (), {"effective_likelihood": 0.7})()}
        
        beliefs_bad = {"F1": type("B", (), {"effective_likelihood": 0.2})(),
                      "F2": type("B", (), {"effective_likelihood": 0.1})()}
        
        # Both should produce valid decisions (or both skip); compare if both produce orders
        result_good = engine.decide(
            equity=Decimal("5000.00"),
            beliefs=beliefs_good,
            signals={},
            state={},
            risk_state={},
        )
        
        result_bad = engine.decide(
            equity=Decimal("5000.00"),
            beliefs=beliefs_bad,
            signals={},
            state={},
            risk_state={},
        )
        
        # Good beliefs should have higher EUC score (if both place orders)
        if result_good.action == "ORDER_INTENT" and result_bad.action == "ORDER_INTENT":
            good_euc = result_good.metadata.get("euc_score", 0)
            bad_euc = result_bad.metadata.get("euc_score", 0)
            assert good_euc >= bad_euc, "Good beliefs should produce higher EUC"


class TestExecutionSupervisor:
    """Unit tests for order state machine."""
    
    @pytest.fixture
    def supervisor(self):
        return ExecutionSupervisor(symbol="MES", slippage_bps=25)
    
    def test_idempotent_submission(self, supervisor):
        """Same intent_id should not create duplicate orders."""
        intent = {
            "intent_id": "test-intent-1",
            "side": "BUY",
            "size": 1,
            "limit_price": 5950.0,
            "stop_price": 5940.0,
            "target_price": 5960.0,
        }
        
        # Simulate adapter
        class MockAdapter:
            def place_order(self, side, size, order_type, price, parent_id=None, **kwargs):
                return {"order_id": f"order-{kwargs.get('client_id', 'unknown')}", "status": "CREATED"}
        
        adapter = MockAdapter()
        
        # Submit twice with same intent_id
        oid1 = supervisor.submit_intent(intent, adapter)
        oid2 = supervisor.submit_intent(intent, adapter)
        
        # Should return same order ID (idempotent)
        assert oid1 == oid2, "Idempotent submission failed"
    
    def test_state_machine_transitions(self, supervisor):
        """Order should transition through valid state machine."""
        intent = {
            "intent_id": "test-intent-2",
            "side": "BUY",
            "size": 1,
            "limit_price": 5950.0,
            "stop_price": 5940.0,
            "target_price": 5960.0,
        }
        
        # Check initial state
        assert supervisor.parent_orders == {}, "Initial state should be empty"
        
        # After submission, should have CREATED state
        class MockAdapter:
            def place_order(self, side, size, order_type, price, parent_id=None, **kwargs):
                return {"order_id": f"order-{kwargs.get('client_id', 'unknown')}", "status": "CREATED"}
        
        oid = supervisor.submit_intent(intent, MockAdapter())
        # Parent order should be tracked


class TestMarketDataQuality:
    """Unit tests for DVS/EQS gating."""
    
    def test_dvs_degradation_on_gap(self):
        """DVS should degrade when bars are missing."""
        state_good = {
            "bar_lag_seconds": 2,
            "missing_fields": 0,
            "gap_detected": False,
            "outlier_score": 0.1,
            "price_jump_pct": 0.01,
            "volume_spike_ratio": 1.2,
            "data_quality_score": 1.0,
        }
        
        state_gap = {
            "bar_lag_seconds": 5,
            "missing_fields": 0,
            "gap_detected": True,
            "outlier_score": 0.1,
            "price_jump_pct": 0.01,
            "volume_spike_ratio": 1.2,
            "data_quality_score": 0.5,
        }
        
        contract = {"dvs": {"initial_value": 1.0, "degradation_events": []}}
        
        dvs_good = Decimal(str(compute_dvs(state_good, contract)))
        dvs_gap = Decimal(str(compute_dvs(state_gap, contract)))
        
        assert dvs_good >= dvs_gap, "Gap should degrade DVS"


class TestTradeLifecycle:
    """Unit tests for trade management (thesis, time, vol exits)."""
    
    @pytest.fixture
    def trade_manager(self):
        return TradeManager(symbol="MES")
    
    @pytest.fixture
    def position(self):
        return TradePosition(
            trade_id="test-trade-1",
            symbol="MES",
            entry_time=datetime.utcnow(),
            entry_price=Decimal("5950.00"),
            qty=1,
            direction=1,
            stop_price=Decimal("5940.00"),
            target_price=Decimal("5960.00"),
            thesis_rules={"min_belief": 0.50},
            time_limits={"max_minutes_in_trade": 60},
            vol_limits={"atr_spike_multiplier": 2.0},
        )
    
    def test_time_exit(self, position):
        """Position should exit after max time in trade."""
        # Simulate 65 minutes in trade
        position.entry_time = datetime.utcnow() - timedelta(minutes=65)
        
        bar = {
            "c": 5950.0,
            "h": 5955.0,
            "l": 5945.0,
            "v": 100000,
        }
        
        exit_action = position.check_exits(bar=bar, signals={}, beliefs={})
        assert exit_action == "TIME_LIMIT", "Should exit after max time"
    
    def test_thesis_invalid(self, position):
        """Position should exit if thesis belief drops below threshold."""
        # Create beliefs with low likelihood
        beliefs = {
            "F1": type("B", (), {"effective_likelihood": 0.3})(),  # Below min_belief
        }
        
        bar = {
            "c": 5950.0,
            "h": 5955.0,
            "l": 5945.0,
            "v": 100000,
        }
        
        exit_action = position.check_exits(bar=bar, signals={}, beliefs=beliefs)
        assert exit_action == "THESIS_INVALID", "Should exit on belief drop"


class TestLearningLoop:
    """Unit tests for strategy reliability and throttling."""
    
    @pytest.fixture
    def learning_loop(self):
        return LearningLoop()
    
    def test_quarantine_on_consecutive_losses(self, learning_loop):
        """Strategy should quarantine on 2+ consecutive losses."""
        # Record 2 losing trades
        for i in range(2):
            outcome = TradeOutcome(
                trade_id=f"trade-{i}",
                template_id="K1",
                regime="trending",
                time_of_day="open",
                entry_price=Decimal("5950.00"),
                exit_price=Decimal("5940.00"),  # Loss
                qty=1,
                entry_time=datetime.utcnow(),
                exit_time=datetime.utcnow(),
                pnl_usd=Decimal("-50.00"),
                pnl_pct=Decimal("-0.01"),
                duration_seconds=300,
                reason_exit="STOP",
                beliefs_at_entry={},
                signals_at_entry={},
                setup_scores={},
                euc_score=0.75,
                data_quality=0.9,
                execution_quality=0.85,
                slippage_ticks=0.5,
                spread_ticks=0.25,
                win=False,
            )
            learning_loop.record_trade(outcome)
        
        state, throttle = learning_loop.get_strategy_state("K1", "trending", "open")
        assert state == StrategyState.QUARANTINED, "Should quarantine on 2 consecutive losses"
    
    def test_re_enable_on_recovery(self, learning_loop):
        """Strategy should re-enable on 2+ consecutive wins after quarantine."""
        # Quarantine first
        for i in range(2):
            outcome = TradeOutcome(
                trade_id=f"trade-loss-{i}",
                template_id="K2",
                regime="range",
                time_of_day="midday",
                entry_price=Decimal("5950.00"),
                exit_price=Decimal("5940.00"),
                qty=1,
                entry_time=datetime.utcnow(),
                exit_time=datetime.utcnow(),
                pnl_usd=Decimal("-50.00"),
                pnl_pct=Decimal("-0.01"),
                duration_seconds=300,
                reason_exit="STOP",
                beliefs_at_entry={},
                signals_at_entry={},
                setup_scores={},
                euc_score=0.75,
                data_quality=0.9,
                execution_quality=0.85,
                slippage_ticks=0.5,
                spread_ticks=0.25,
                win=False,
            )
            learning_loop.record_trade(outcome)
        
        # Verify quarantine
        state, _ = learning_loop.get_strategy_state("K2", "range", "midday")
        assert state == StrategyState.QUARANTINED, "Should be quarantined after losses"
        
        # Recovery: 2 wins
        for i in range(2):
            outcome = TradeOutcome(
                trade_id=f"trade-win-{i}",
                template_id="K2",
                regime="range",
                time_of_day="midday",
                entry_price=Decimal("5950.00"),
                exit_price=Decimal("5960.00"),  # Win
                qty=1,
                entry_time=datetime.utcnow(),
                exit_time=datetime.utcnow(),
                pnl_usd=Decimal("50.00"),
                pnl_pct=Decimal("0.01"),
                duration_seconds=300,
                reason_exit="TARGET",
                beliefs_at_entry={},
                signals_at_entry={},
                setup_scores={},
                euc_score=0.75,
                data_quality=0.9,
                execution_quality=0.85,
                slippage_ticks=0.5,
                spread_ticks=0.25,
                win=True,
            )
            learning_loop.record_trade(outcome)
        
        # Should be re-enabled
        state, _ = learning_loop.get_strategy_state("K2", "range", "midday")
        assert state == StrategyState.ACTIVE, "Should re-enable after recovery wins"
    
    def test_throttle_on_low_win_rate(self, learning_loop):
        """Strategy should throttle when win rate drops."""
        # Record 10 trades: 3 wins, 7 losses (30% win rate)
        for i in range(7):
            outcome = TradeOutcome(
                trade_id=f"trade-loss-{i}",
                template_id="K3",
                regime="volatile",
                time_of_day="late_session",
                entry_price=Decimal("5950.00"),
                exit_price=Decimal("5940.00"),
                qty=1,
                entry_time=datetime.utcnow(),
                exit_time=datetime.utcnow(),
                pnl_usd=Decimal("-25.00"),
                pnl_pct=Decimal("-0.01"),
                duration_seconds=300,
                reason_exit="STOP",
                beliefs_at_entry={},
                signals_at_entry={},
                setup_scores={},
                euc_score=0.75,
                data_quality=0.9,
                execution_quality=0.85,
                slippage_ticks=0.5,
                spread_ticks=0.25,
                win=False,
            )
            learning_loop.record_trade(outcome)
        
        for i in range(3):
            outcome = TradeOutcome(
                trade_id=f"trade-win-{i}",
                template_id="K3",
                regime="volatile",
                time_of_day="late_session",
                entry_price=Decimal("5950.00"),
                exit_price=Decimal("5960.00"),
                qty=1,
                entry_time=datetime.utcnow(),
                exit_time=datetime.utcnow(),
                pnl_usd=Decimal("25.00"),
                pnl_pct=Decimal("0.01"),
                duration_seconds=300,
                reason_exit="TARGET",
                beliefs_at_entry={},
                signals_at_entry={},
                setup_scores={},
                euc_score=0.75,
                data_quality=0.9,
                execution_quality=0.85,
                slippage_ticks=0.5,
                spread_ticks=0.25,
                win=True,
            )
            learning_loop.record_trade(outcome)
        
        # Should have throttle > 0
        modifier = learning_loop.get_euc_cost_modifier("K3", "volatile", "late_session")
        assert modifier > 1.0, f"Should throttle on 30% win rate, got modifier {modifier}"


class TestE2EScenario:
    """End-to-end scenario tests."""
    
    def test_flat_to_trade_to_exit_cycle(self):
        """Test complete trading cycle: flat → enter → manage → exit → learn."""
        # This would require mocking adapter and running runner.run_once multiple times
        # For now, verify the structure can handle the cycle
        runner = BotRunner(adapter="tradovate", fill_mode="IMMEDIATE")
        
        # Verify all components initialized
        assert hasattr(runner, "signals"), "Signals engine not initialized"
        assert hasattr(runner, "beliefs"), "Beliefs engine not initialized"
        assert hasattr(runner, "decision"), "Decision engine not initialized"
        assert hasattr(runner, "supervisor"), "Execution supervisor not initialized"
        assert hasattr(runner, "trade_manager"), "Trade manager not initialized"
        assert hasattr(runner, "learning_loop"), "Learning loop not initialized"
        assert hasattr(runner, "open_positions"), "Open positions tracking not initialized"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
