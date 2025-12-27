"""
E2E Demo: Day in the Life of the Trading Bot

Simulates a complete trading day:
1. Bot starts flat
2. First signal detected (K1 VWAP MR)
3. Entry placed, order ACK'd, filled
4. Position managed in-flight (check thesis, time, vol exits)
5. Exit triggered (thesis invalid or target/stop hit)
6. Trade outcome recorded to learning loop
7. Throttle applied to K1 on losses
8. Second signal detected (K2 Failed Break)
9. Entry, manage, exit, learn
10. Summary: 2 trades, learning loop state updated

Run with:
  python -m trading_bot.tools.e2e_demo_scenario
"""

from typing import Dict, Any, List
from decimal import Decimal
from datetime import datetime, timedelta
from dataclasses import asdict

# Mock bar data simulating a trading day
MOCK_BARS = [
    # Hour 1: RTH open, quiet market
    {"ts": "2025-01-02T09:30:00-05:00", "o": 5820, "h": 5825, "l": 5815, "c": 5820, "v": 5000, "lag_seconds": 1, "data_quality_score": 0.95},
    {"ts": "2025-01-02T09:31:00-05:00", "o": 5820, "h": 5828, "l": 5818, "c": 5822, "v": 4800, "lag_seconds": 1, "data_quality_score": 0.95},
    {"ts": "2025-01-02T09:32:00-05:00", "o": 5822, "h": 5830, "l": 5820, "c": 5825, "v": 5200, "lag_seconds": 1, "data_quality_score": 0.95},
    
    # Hour 2: Pullback setup (K1 VWAP MR detectable)
    {"ts": "2025-01-02T10:30:00-05:00", "o": 5835, "h": 5838, "l": 5815, "c": 5818, "v": 6000, "lag_seconds": 1, "data_quality_score": 0.92},
    {"ts": "2025-01-02T10:31:00-05:00", "o": 5818, "h": 5822, "l": 5810, "c": 5815, "v": 5500, "lag_seconds": 1, "data_quality_score": 0.93},  # <- K1 VWAP MR setup
    {"ts": "2025-01-02T10:32:00-05:00", "o": 5815, "h": 5820, "l": 5810, "c": 5818, "v": 5200, "lag_seconds": 1, "data_quality_score": 0.94},  # <- Entry filled
    
    # Hour 3: Trade management (K1 position held, thesis valid)
    {"ts": "2025-01-02T11:30:00-05:00", "o": 5818, "h": 5828, "l": 5817, "c": 5825, "v": 5800, "lag_seconds": 1, "data_quality_score": 0.94},  # +7 ticks, TP approaching
    {"ts": "2025-01-02T11:31:00-05:00", "o": 5825, "h": 5830, "l": 5823, "c": 5828, "v": 5300, "lag_seconds": 1, "data_quality_score": 0.95},  # +10 ticks, TP hit!
    
    # Hour 4: Position exited, thesis checked (valid exit)
    # K1 trade closed: Entry 5817.75, Exit 5828, +10.25 ticks = +$127.81
    
    # Hour 5: Market consolidates, Failed Break setup (K2) detectable
    {"ts": "2025-01-02T13:30:00-05:00", "o": 5828, "h": 5835, "l": 5825, "c": 5833, "v": 5000, "lag_seconds": 1, "data_quality_score": 0.93},
    {"ts": "2025-01-02T13:31:00-05:00", "o": 5833, "h": 5838, "l": 5830, "c": 5835, "v": 5400, "lag_seconds": 1, "data_quality_score": 0.92},  # <- Break attempt
    {"ts": "2025-01-02T13:32:00-05:00", "o": 5835, "h": 5839, "l": 5825, "c": 5828, "v": 6200, "lag_seconds": 1, "data_quality_score": 0.91},  # <- Break fails (K2 setup)
    
    # Hour 6: K2 Failed Break entry setup
    {"ts": "2025-01-02T14:30:00-05:00", "o": 5828, "h": 5835, "l": 5820, "c": 5822, "v": 5800, "lag_seconds": 1, "data_quality_score": 0.93},  # <- K2 Short setup
    {"ts": "2025-01-02T14:31:00-05:00", "o": 5822, "h": 5828, "l": 5815, "c": 5818, "v": 5400, "lag_seconds": 1, "data_quality_score": 0.94},  # <- Entry filled
    
    # Hour 7: K2 trade management (breaks to downside)
    {"ts": "2025-01-02T15:30:00-05:00", "o": 5818, "h": 5825, "l": 5805, "c": 5810, "v": 6500, "lag_seconds": 1, "data_quality_score": 0.92},  # -8 ticks
    {"ts": "2025-01-02T15:31:00-05:00", "o": 5810, "h": 5820, "l": 5800, "c": 5805, "v": 6200, "lag_seconds": 1, "data_quality_score": 0.93},  # -13 ticks, but TP is -5, so exit
    
    # Hour 8: K2 exit (loss)
    # K2 trade closed: Entry 5828.50, Exit 5805, -23.50 ticks = -$293.75 (LOSS)
    
    # Hour 9: Day close
    {"ts": "2025-01-02T16:00:00-05:00", "o": 5805, "h": 5810, "l": 5800, "c": 5808, "v": 4500, "lag_seconds": 2, "data_quality_score": 0.90},
]


def mock_signal_generator(bar: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Generate mock signals that evolve throughout the day."""
    close = Decimal(str(bar["c"]))
    
    # K1 setup: VWAP MR detectable after bar 4
    if 4 <= index <= 7:
        s1_vwap_mr = 0.75
        s8_momentum = 0.30
    else:
        s1_vwap_mr = 0.50
        s8_momentum = 0.55
    
    # K2 setup: Break failure detectable after bar 9
    if 9 <= index <= 11:
        s5_break_failure = 0.80
    else:
        s5_break_failure = 0.40
    
    signals = {
        "S1_VWAP_MR": s1_vwap_mr,
        "S5_BREAK_FAILURE": s5_break_failure,
        "S6_NOISE": 0.30,
        "S8_MOMENTUM": s8_momentum,
        "S13_SWEEP": 0.40,
        "spread_proxy_tickiness": 0.5,
        "session_phase": 2 + (index // 6),  # Advance phase every 6 bars
    }
    
    return signals


def mock_belief_generator(bar: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Generate mock beliefs that evolve throughout the day."""
    # K1 setup: F1 (VWAP MR) strong after bar 4
    if 4 <= index <= 7:
        f1_likelihood = 0.70
        f1_stability = 0.85
    else:
        f1_likelihood = 0.45
        f1_stability = 0.60
    
    # K2 setup: F2 (Failed Break) strong after bar 9
    if 9 <= index <= 11:
        f2_likelihood = 0.72
        f2_stability = 0.80
    else:
        f2_likelihood = 0.40
        f2_stability = 0.50
    
    beliefs = {
        "F1_VWAP_MR": {
            "constraint_id": "F1_VWAP_MR",
            "likelihood": f1_likelihood,
            "effective_likelihood": f1_likelihood,
            "stability": f1_stability,
        },
        "F2_FAILED_BREAK": {
            "constraint_id": "F2_FAILED_BREAK",
            "likelihood": f2_likelihood,
            "effective_likelihood": f2_likelihood,
            "stability": f2_stability,
        },
        "F3_SWEEP_REVERSAL": {
            "constraint_id": "F3_SWEEP_REVERSAL",
            "likelihood": 0.35,
            "effective_likelihood": 0.35,
            "stability": 0.60,
        },
        "F4_MOMENTUM": {
            "constraint_id": "F4_MOMENTUM",
            "likelihood": 0.40,
            "effective_likelihood": 0.40,
            "stability": 0.55,
        },
        "F5_NOISE_FILTER": {
            "constraint_id": "F5_NOISE_FILTER",
            "likelihood": 0.70,
            "effective_likelihood": 0.70,
            "stability": 0.75,
        },
    }
    
    return beliefs


def run_e2e_demo():
    """Run complete E2E demo."""
    print("\n" + "="*80)
    print("TRADING BOT E2E DEMO: Day in the Life")
    print("="*80 + "\n")
    
    # Initialize bot components
    from trading_bot.core.runner import BotRunner
    
    print("[INIT] Creating BotRunner...")
    try:
        runner = BotRunner(
            contracts_path="src/trading_bot/contracts",
            db_path="data/demo_events.sqlite",
            adapter="tradovate",  # SIM mode
        )
        print("[OK] BotRunner initialized")
        print(f"  Equity fallback: ${runner.adapter.get_account_snapshot().get('equity', 1000)}")
        print(f"  Signal engine: {len(runner.signals.__dict__.get('signals', {}))} signals loaded")
        print(f"  Decision engine: {len(runner.decision.templates)} templates loaded\n")
    except Exception as e:
        print(f"[ERROR] Failed to init BotRunner: {e}")
        return
    
    # Track demo state
    trades_executed = []
    trades_exited = []
    learning_updates = []
    
    print("[TRADING] Starting simulation...")
    print("-" * 80)
    
    # Simulate each bar
    for bar_idx, bar in enumerate(MOCK_BARS):
        ts = bar["ts"]
        close = Decimal(str(bar["c"]))
        
        print(f"\nBar {bar_idx + 1}: {ts} | Close: {float(close):.2f}")
        
        # Generate mock signals and beliefs
        signals = mock_signal_generator(bar, bar_idx)
        beliefs = mock_belief_generator(bar, bar_idx)
        
        # Enrich bar with signal/belief data
        bar_enriched = {**bar, "signals": signals, "beliefs": beliefs}
        
        try:
            # Run bot cycle
            result = runner.run_once(bar_enriched)
            
            # Track trade events
            if result.get("action") == "ORDER_INTENT":
                print(f"  [DECISION] ORDER_INTENT - {result.get('reason')}")
                if runner.open_positions:
                    latest_trade_id = list(runner.open_positions.keys())[-1]
                    trades_executed.append({
                        "bar_idx": bar_idx,
                        "trade_id": latest_trade_id,
                        "entry_price": float(close),
                        "template_id": result.get("metadata", {}).get("template_id", "UNKNOWN"),
                    })
                    print(f"    Trade entered: {latest_trade_id}")
            
            elif result.get("action") == "SKIP":
                print(f"  [DECISION] SKIP - {result.get('reason')}")
            
            # Check for trade exits
            events = runner.events.query_recent(limit=100) if hasattr(runner.events, "query_recent") else []
            for evt in events:
                if evt.get("event_type") == "TRADE_MANAGEMENT_EXIT":
                    data = evt.get("data", {})
                    trade_id = data.get("trade_id", "UNKNOWN")
                    pnl = data.get("pnl_usd", 0)
                    duration = data.get("duration_seconds", 0)
                    print(f"  [EXIT] Trade {trade_id} closed | PnL: ${pnl:.2f} | Duration: {duration}s")
                    trades_exited.append({
                        "bar_idx": bar_idx,
                        "trade_id": trade_id,
                        "exit_price": float(close),
                        "pnl": pnl,
                    })
                
                elif evt.get("event_type") == "LEARNING_UPDATE":
                    data = evt.get("data", {})
                    learning_updates.append({
                        "bar_idx": bar_idx,
                        "update": data,
                    })
                    print(f"  [LEARNING] Metrics updated for {data.get('strategy_key')}")
        
        except Exception as e:
            print(f"  [ERROR] Bar processing failed: {e}")
    
    # Print summary
    print("\n" + "="*80)
    print("DEMO SUMMARY")
    print("="*80)
    
    print(f"\nTrades Executed: {len(trades_executed)}")
    for trade in trades_executed:
        print(f"  Bar {trade['bar_idx']}: {trade['template_id']} @ {trade['entry_price']:.2f}")
    
    print(f"\nTrades Exited: {len(trades_exited)}")
    total_pnl = 0.0
    for trade in trades_exited:
        print(f"  Bar {trade['bar_idx']}: PnL ${trade['pnl']:.2f}")
        total_pnl += trade['pnl']
    
    print(f"\nLearning Updates: {len(learning_updates)}")
    for update in learning_updates:
        print(f"  Bar {update['bar_idx']}: {update['update']}")
    
    print(f"\nTotal P&L: ${total_pnl:.2f}")
    
    # Print learning loop state
    print("\nLearning Loop Metrics:")
    metrics_summary = runner.learning_loop.get_metrics_summary()
    if metrics_summary:
        for strategy_key, metrics in metrics_summary.items():
            print(f"  {strategy_key}: {metrics}")
    else:
        print("  (No metrics recorded)")
    
    # Print strategy states
    print("\nStrategy States:")
    strategy_states = runner.learning_loop.get_all_metrics()
    for strategy_key, metrics in strategy_states.items():
        print(f"  {strategy_key}: {metrics.state.name} (throttle level {metrics.throttle_level})")
    
    print("\n" + "="*80)
    print("Demo complete!")
    print("="*80 + "\n")


if __name__ == "__main__":
    run_e2e_demo()
