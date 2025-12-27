"""Verify all core bot components are in place and connected."""
import sys
import inspect
import json

checks = {}

# 1. Check: Shared readiness module
try:
    from trading_bot.engines.readiness import compute_readiness_snapshot
    sig = inspect.signature(compute_readiness_snapshot)
    checks['readiness_module'] = {
        'exists': True,
        'callable': callable(compute_readiness_snapshot),
        'params': list(sig.parameters.keys()),
        'status': 'PASS'
    }
except Exception as e:
    checks['readiness_module'] = {'exists': False, 'error': str(e), 'status': 'FAIL'}

# 2. Check: IBKR adapter has all critical methods
try:
    from trading_bot.adapters.ibkr_adapter import IBKRAdapter
    methods = [m for m in dir(IBKRAdapter) if not m.startswith('_') or m == '_resolve_primary_contract']
    checks['adapter_methods'] = {
        'has_assert_execution_allowed': 'assert_execution_allowed' in methods,
        'has_get_market_context': 'get_market_context' in methods,
        'has_get_status': 'get_status' in methods,
        'has_resolve_primary_contract': '_resolve_primary_contract' in methods,
        'has_req_historical_bars': 'req_historical_bars' in methods,
        'status': 'PASS' if all([
            'assert_execution_allowed' in methods,
            'get_market_context' in methods,
            'get_status' in methods,
            '_resolve_primary_contract' in methods,
        ]) else 'FAIL'
    }
except Exception as e:
    checks['adapter_methods'] = {'error': str(e), 'status': 'FAIL'}

# 3. Check: Runner emits market_context in DECISION_1M
try:
    with open('src/trading_bot/core/runner.py', 'r') as f:
        runner_code = f.read()
        checks['runner'] = {
            'has_market_context_in_decision': 'market_context = self.adapter.get_market_context' in runner_code,
            'has_readiness_import': 'from trading_bot.engines.readiness import' in runner_code,
            'emits_readiness_snapshot': 'READINESS_SNAPSHOT' in runner_code,
            'status': 'PASS' if 'market_context' in runner_code and 'READINESS_SNAPSHOT' in runner_code else 'FAIL'
        }
except Exception as e:
    checks['runner'] = {'error': str(e), 'status': 'FAIL'}

# 4. Check: CLI has preflight command with all flags
try:
    with open('src/trading_bot/cli.py', 'r') as f:
        cli_code = f.read()
        checks['cli'] = {
            'has_preflight_cmd': 'args.cmd == "preflight"' in cli_code,
            'has_readiness_flags': '--print-json' in cli_code and '--quiet' in cli_code and '--outfile' in cli_code,
            'has_preflight_logic': '"go": go' in cli_code,
            'has_hard_blockers': 'NOT_CONNECTED' in cli_code and 'INSUFFICIENT_DTE' in cli_code,
            'status': 'PASS' if all([
                'args.cmd == "preflight"' in cli_code,
                '--print-json' in cli_code,
                '"go": go' in cli_code,
                'NOT_CONNECTED' in cli_code,
            ]) else 'FAIL'
        }
except Exception as e:
    checks['cli'] = {'error': str(e), 'status': 'FAIL'}

# 5. Check: market_context returns fully shaped dict with no nulls policy
try:
    with open('src/trading_bot/adapters/ibkr_adapter.py', 'r') as f:
        adapter_code = f.read()
        checks['market_context_shape'] = {
            'always_returns_dict': 'return {' in adapter_code and 'get_market_context' in adapter_code,
            'includes_connected': '"connected": connected' in adapter_code,
            'includes_dq': '"data_quality": dq' in adapter_code,
            'includes_dte': '"dte": dte' in adapter_code,
            'has_explicit_defaults': 'dq = "NONE"' in adapter_code or 'dq = "UNKNOWN"' in adapter_code,
            'status': 'PASS' if '"connected": connected' in adapter_code else 'FAIL'
        }
except Exception as e:
    checks['market_context_shape'] = {'error': str(e), 'status': 'FAIL'}

# 6. Check: DTE filter in resolver with min_days_to_expiry
try:
    with open('src/trading_bot/adapters/ibkr_adapter.py', 'r') as f:
        adapter_code = f.read()
        checks['dte_filter'] = {
            'has_min_days_to_expiry_param': 'min_days_to_expiry: int = 5' in adapter_code,
            'filters_by_dte': 'dte >= min_days_to_expiry' in adapter_code,
            'has_fallback': 'all_valid.sort' in adapter_code,
            'status': 'PASS' if 'min_days_to_expiry: int = 5' in adapter_code else 'FAIL'
        }
except Exception as e:
    checks['dte_filter'] = {'error': str(e), 'status': 'FAIL'}

# 7. Check: Status includes DTE and contract_month
try:
    with open('src/trading_bot/adapters/ibkr_adapter.py', 'r') as f:
        adapter_code = f.read()
        checks['status_output'] = {
            'includes_dte': '"dte": dte,' in adapter_code,
            'includes_contract_month': '"contract_month": contract_month,' in adapter_code,
            'includes_primary_contract': '"primary_contract": primary_contract,' in adapter_code,
            'status': 'PASS' if '"dte": dte,' in adapter_code and '"contract_month": contract_month,' in adapter_code else 'FAIL'
        }
except Exception as e:
    checks['status_output'] = {'error': str(e), 'status': 'FAIL'}

# Summary
total_checks = len([c for c in checks.values() if c.get('status') == 'PASS'])
total = len([c for c in checks.values() if 'status' in c])

print(json.dumps(checks, indent=2))
print(f"\n✓ {total_checks}/{total} major components verified PASS")
