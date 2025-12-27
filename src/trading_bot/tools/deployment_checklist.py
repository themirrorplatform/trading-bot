"""
PRODUCTION DEPLOYMENT CHECKLIST & VALIDATION GUIDE

Final validation before taking capital live on IBKR.
Covers: kill switch testing, daily loss limits, frequency caps, margin safety, disaster recovery.
"""

import json
from datetime import datetime
from typing import Dict, List, Any


DEPLOYMENT_CHECKLIST = {
    "PHASE 0: Pre-Deployment Setup": {
        "tasks": [
            "✓ IBKR account set up (paper trading enabled first)",
            "✓ API credentials configured (read TWS settings)",
            "✓ Market data subscriptions active (Level 1 at minimum)",
            "✓ Risk model capital tiers validated against account equity",
            "✓ Constitution limits reviewed ($15 max risk, 12-tick stop, 2 trades/day, $30 daily loss cap)",
            "✓ Kill switch callback implemented and tested",
            "✓ Logging and audit trail configured",
        ]
    },
    
    "PHASE 1: Kill Switch & Safety Limits": {
        "tasks": [
            "[ ] Kill switch manual activation tested (position should flatten in < 5s)",
            "[ ] Kill switch automatic trigger on lost connection (reconciliation detects)",
            "[ ] Kill switch automatic trigger on data quality gate failure (DVS < 0.30)",
            "[ ] Kill switch on margin call detected (buying power < 0)",
            "[ ] Kill switch on daily loss limit ($30 reached → no new orders, flatten EOD)",
            "[ ] Kill switch on frequency limit (2 trades in day → no new orders)",
            "[ ] Kill switch on consecutive loss limit (2 consecutive losses → no new orders)",
            "[ ] All kill switch events logged with timestamp and reason",
        ]
    },
    
    "PHASE 2: Order Lifecycle Supervision": {
        "tasks": [
            "[ ] Bracket order submission tested (entry + stop + target all created)",
            "[ ] Idempotent order IDs tested (restart should NOT duplicate orders)",
            "[ ] Order status translation working (NEW → WORKING → FILLED)",
            "[ ] Partial fill handling tested (multiple FILL events aggregated correctly)",
            "[ ] Order timeout and cancellation (TTL = 90s on stuck orders)",
            "[ ] Order reconciliation on startup (compare broker state to local state)",
            "[ ] Orphaned order detection (fills without matching order in system)",
            "[ ] Order state machine error recovery (repair missing children, etc.)",
        ]
    },
    
    "PHASE 3: Position Reconciliation": {
        "tasks": [
            "[ ] Position snapshot on startup (actual broker position queried)",
            "[ ] Expected vs actual position comparison (every 2 minutes)",
            "[ ] Mismatch detection triggers kill switch (conservative: flatten and alert)",
            "[ ] Fill event processing (qty tracked, entry price averaged)",
            "[ ] Position close detection (qty → 0)",
            "[ ] Partial exit handling (reduce size, maintain stop/target)",
            "[ ] Forced flatten on error (market order if TTL or position desync)",
        ]
    },
    
    "PHASE 4: Data Quality Gating": {
        "tasks": [
            "[ ] DVS computation and gating (< 0.80 blocks new orders)",
            "[ ] EQS computation and gating (< 0.75 blocks new orders)",
            "[ ] Data gap detection (missing bars for 90+ seconds)",
            "[ ] Stale feed detection (price stuck + no volume)",
            "[ ] Spread anomaly detection (> 10 ticks)",
            "[ ] Outlier detection (true range >> ATR30)",
            "[ ] Quality score logging per bar",
            "[ ] Recovery from quality gate failure (when DVS/EQS recover, trading resumes)",
        ]
    },
    
    "PHASE 5: Trade Lifecycle Management": {
        "tasks": [
            "[ ] Entry detection and planning (signals + beliefs assessed)",
            "[ ] Position entry with thesis tracking (min belief % stored)",
            "[ ] In-flight thesis validation (belief drop → exit)",
            "[ ] Time-based exits (max minutes in trade enforced)",
            "[ ] Volatility-based exits (ATR spike tightens stop)",
            "[ ] Stop loss protection (never moved above entry)",
            "[ ] Take profit target execution (closed on hit or surpassed)",
            "[ ] Trade outcome recording (PnL, duration, reason captured)",
        ]
    },
    
    "PHASE 6: Learning Loop & Strategy Throttling": {
        "tasks": [
            "[ ] Trade outcome recording (entry/exit/PnL/reason/beliefs captured)",
            "[ ] Win rate tracking per strategy/regime/TOD",
            "[ ] Expectancy computation (E[PnL] per trade)",
            "[ ] Quarantine logic (2+ losses or negative expectancy → disabled)",
            "[ ] Throttle level computation (win rate < 40% → add friction)",
            "[ ] EUC cost modifier applied (throttle level 1→1.2x, level 2→1.5x)",
            "[ ] Re-enable logic (2+ wins or positive expectancy → restore)",
            "[ ] State changes logged to audit trail",
        ]
    },
    
    "PHASE 7: Margin & Buying Power Management": {
        "tasks": [
            "[ ] Buying power query on each cycle (dynamic, not cached)",
            "[ ] Account equity snapshot (NetLiquidation tracked)",
            "[ ] Tier gating by capital (S tier if equity < $1,500)",
            "[ ] Position sizing by risk budget ($15 max per trade)",
            "[ ] Margin requirement check (conservative: 2x buffer)",
            "[ ] Margin call detection (available funds < 0)",
            "[ ] Forced deleveraging on margin pressure (reduce positions)",
        ]
    },
    
    "PHASE 8: Audit & Compliance Logging": {
        "tasks": [
            "[ ] Event store capturing all decisions and outcomes",
            "[ ] Decision journal with plain-English explanations",
            "[ ] Trade journal with entry/exit/PnL/reason",
            "[ ] Learning loop state changes logged",
            "[ ] Kill switch events logged with cause",
            "[ ] Reconciliation mismatches logged (for investigation)",
            "[ ] Logs exportable to CSV for manual review",
            "[ ] Log retention policy (30 days minimum)",
        ]
    },
    
    "PHASE 9: Disaster Recovery & Restart": {
        "tasks": [
            "[ ] Graceful shutdown (flush pending orders, save state)",
            "[ ] State persistence (strategy throttle levels, learning metrics saved)",
            "[ ] Restart recovery (reload state, reconcile with broker)",
            "[ ] Connection loss recovery (reconnect, full reconciliation)",
            "[ ] Duplicate order prevention (idempotent order IDs)",
            "[ ] Market gap handling (resume trading after data recovery)",
            "[ ] Rollback on fatal error (kill switch + human review)",
        ]
    },
    
    "PHASE 10: Human Oversight & Manual Controls": {
        "tasks": [
            "[ ] Manual kill switch (one-click flatten all positions)",
            "[ ] Manual order cancellation (per order or batch)",
            "[ ] Manual position close (if broker state desyncs)",
            "[ ] Audit trail viewable in real-time (web dashboard or CLI)",
            "[ ] Alerts for kill switch events (email/Slack to operator)",
            "[ ] Daily reconciliation report (trades, PnL, learning state)",
            "[ ] Exception queue for manual review (failed orders, mismatches)",
        ]
    }
}


def print_checklist():
    """Print deployment checklist."""
    print("\n" + "="*80)
    print("TRADING BOT PRODUCTION DEPLOYMENT CHECKLIST")
    print("="*80 + "\n")
    
    for phase, content in DEPLOYMENT_CHECKLIST.items():
        print(f"\n{phase}")
        print("-" * 80)
        for task in content["tasks"]:
            status = "DONE" if task.startswith("✓") else "PENDING"
            task_text = task.replace("✓", "").replace("[ ]", "").strip()
            print(f"  [{status}] {task_text}")


def validate_safety_limits():
    """Validate that safety limits are correctly configured."""
    print("\n" + "="*80)
    print("SAFETY LIMITS VALIDATION")
    print("="*80 + "\n")
    
    from trading_bot.core.config import load_yaml_contract
    
    try:
        risk_model = load_yaml_contract("src/trading_bot/contracts", "risk_model.yaml")
        
        limits = {
            "max_risk_usd": (risk_model.get("max_risk_usd"), 15),
            "max_stop_ticks": (risk_model.get("max_stop_ticks"), 12),
            "max_trades_per_day": (risk_model.get("max_trades_per_day"), 2),
            "consecutive_losses_limit": (risk_model.get("consecutive_losses_limit"), 2),
            "daily_loss_limit": (risk_model.get("daily_loss_limit"), 30),
        }
        
        all_valid = True
        for limit_name, (actual, expected) in limits.items():
            status = "✓ PASS" if actual == expected else "✗ FAIL"
            print(f"{status}: {limit_name}")
            print(f"      Expected: {expected}, Actual: {actual}")
            if actual != expected:
                all_valid = False
        
        if all_valid:
            print("\n✓ All safety limits validated!")
        else:
            print("\n✗ Safety limits validation FAILED. Do not deploy.")
        
        return all_valid
    except Exception as e:
        print(f"✗ Error loading risk model: {e}")
        return False


def validate_ibkr_connection():
    """Test IBKR connection and basic API calls."""
    print("\n" + "="*80)
    print("IBKR CONNECTION VALIDATION")
    print("="*80 + "\n")
    
    try:
        from trading_bot.adapters.ibkr_adapter import IBKRAdapter
        
        adapter = IBKRAdapter(mode="OBSERVE")  # Start in OBSERVE (paper)
        
        print("[ ] Adapter created")
        
        # Test connection
        if hasattr(adapter, 'connect'):
            adapter.connect()
            print("[ ] Connection established")
        
        # Test account snapshot
        snapshot = adapter.get_account_snapshot()
        if snapshot:
            print(f"✓ Account snapshot retrieved")
            print(f"    Equity: ${snapshot.get('equity', 'N/A')}")
            print(f"    Buying Power: ${snapshot.get('buying_power', 'N/A')}")
        else:
            print("✗ Failed to retrieve account snapshot")
            return False
        
        # Test position query
        positions = adapter.get_position_snapshot()
        print(f"✓ Positions queried: {positions}")
        
        # Test market data
        last_bar = adapter.get_market_data_quality()
        print(f"✓ Market data quality: {last_bar}")
        
        print("\n✓ IBKR connection validation PASSED!")
        return True
    except Exception as e:
        print(f"\n✗ IBKR connection validation FAILED: {e}")
        return False


def validate_strategy_library():
    """Validate that all 5 strategies load correctly."""
    print("\n" + "="*80)
    print("STRATEGY LIBRARY VALIDATION")
    print("="*80 + "\n")
    
    try:
        from trading_bot.strategies.base import StrategyLibrary
        from trading_bot.strategies.k1_k5_templates import (
            K1_VWAPMeanReversion,
            K2_FailedBreakReversal,
            K3_SweepReversal,
            K4_MomentumExtension,
            K5_NoiseFilter,
        )
        
        library = StrategyLibrary()
        
        strategies = [
            K1_VWAPMeanReversion(),
            K2_FailedBreakReversal(),
            K3_SweepReversal(),
            K4_MomentumExtension(),
            K5_NoiseFilter(),
        ]
        
        for strategy in strategies:
            library.register(strategy)
            print(f"✓ {strategy.template_id}: {strategy.name}")
        
        all_states = library.get_all_states()
        print(f"\n✓ All strategies loaded and ACTIVE")
        for template_id, state in all_states.items():
            print(f"    {template_id}: {state}")
        
        print("\n✓ Strategy library validation PASSED!")
        return True
    except Exception as e:
        print(f"\n✗ Strategy library validation FAILED: {e}")
        return False


def generate_deployment_report(filepath: str = "data/deployment_report.json"):
    """Generate deployment report."""
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "safety_limits": validate_safety_limits(),
            "ibkr_connection": validate_ibkr_connection(),
            "strategy_library": validate_strategy_library(),
        },
        "ready_for_deployment": all([
            validate_safety_limits(),
            validate_ibkr_connection(),
            validate_strategy_library(),
        ]),
    }
    
    with open(filepath, "w") as f:
        json.dump(report, f, indent=2)
    
    print("\n" + "="*80)
    if report["ready_for_deployment"]:
        print("✓ DEPLOYMENT READY")
    else:
        print("✗ DEPLOYMENT NOT READY")
    print("="*80)
    print(f"\nReport saved to: {filepath}\n")
    
    return report


if __name__ == "__main__":
    print_checklist()
    print("\nRunning validation checks...\n")
    report = generate_deployment_report()
