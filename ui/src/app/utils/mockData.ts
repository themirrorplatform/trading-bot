import type {
  Event,
  DecisionRecord,
  Signal,
  Constraint,
  BeliefState,
  ExecutionQuality,
  Trade,
  LearningUpdate,
  ConfigPatch,
  Alert,
  MarketData,
  SystemHealth,
} from '../types/trading-types';

export const mockMarketData: MarketData = {
  symbol: 'MES',
  session: 'RTH',
  last_price: 4567.25,
  change: 12.50,
  change_pct: 0.27,
  spread_proxy: 0.25,
  volatility_proxy: 1.8,
};

export const mockSystemHealth: SystemHealth = {
  data_feed_uptime: 99.98,
  latency_ms: 12,
  missing_bars: 0,
  clock_drift_ms: 3,
  websocket_connected: true,
};

export const mockEvents: Event[] = [
  {
    event_id: 'evt_001',
    timestamp: new Date().toISOString(),
    event_type: 'BAR_CLOSED',
    severity: 'info',
    summary: '5-minute bar closed at 4567.25',
    payload: { close: 4567.25, volume: 1234 },
    reason_codes: [],
  },
  {
    event_id: 'evt_002',
    timestamp: new Date(Date.now() - 1000).toISOString(),
    event_type: 'SIGNALS_COMPUTED',
    severity: 'info',
    summary: '28 signals updated, 3 reliability adjustments',
    payload: { signals_count: 28, adjustments: 3 },
    reason_codes: ['SIGNAL_REFRESH'],
  },
  {
    event_id: 'evt_003',
    timestamp: new Date(Date.now() - 2000).toISOString(),
    event_type: 'BELIEF_UPDATED',
    severity: 'info',
    summary: 'Constraint C_MOMENTUM_REGIME updated (probability 0.72 → 0.78)',
    payload: { constraint: 'C_MOMENTUM_REGIME', old_prob: 0.72, new_prob: 0.78 },
    reason_codes: ['BELIEF_EVOLUTION'],
  },
  {
    event_id: 'evt_004',
    timestamp: new Date(Date.now() - 3000).toISOString(),
    event_type: 'DVS_EQS_UPDATED',
    severity: 'good',
    summary: 'DVS: 0.98, EQS: 0.95 — data quality excellent',
    payload: { dvs: 0.98, eqs: 0.95 },
    reason_codes: [],
  },
  {
    event_id: 'evt_005',
    timestamp: new Date(Date.now() - 4000).toISOString(),
    event_type: 'GATE_FAILED',
    severity: 'warn',
    summary: 'GATE_FRICTION_TOO_HIGH failed (required ≤ 4.75, current 6.20)',
    payload: { gate: 'GATE_FRICTION_TOO_HIGH', required: 4.75, current: 6.20 },
    reason_codes: ['GATE_FRICTION_TOO_HIGH', 'SPREAD_WIDENED'],
  },
  {
    event_id: 'evt_006',
    timestamp: new Date(Date.now() - 5000).toISOString(),
    event_type: 'DECISION_MADE',
    severity: 'warn',
    summary: 'SKIP — Friction gate failed',
    payload: { decision: 'SKIP', euc_score: 2.3 },
    reason_codes: ['GATE_FRICTION_TOO_HIGH'],
  },
];

export const mockDecision: DecisionRecord = {
  decision_id: 'dec_001',
  timestamp: new Date().toISOString(),
  outcome: 'SKIP',
  euc: {
    total: 2.3,
    edge: 5.2,
    uncertainty: 2.1,
    cost: 6.2,
    breakdown: {
      constraint_contributions: [
        {
          constraint_id: 'c_001',
          constraint_name: 'C_MOMENTUM_REGIME',
          contribution: 3.5,
          probability: 0.78,
          dominance_rank: 1,
        },
        {
          constraint_id: 'c_002',
          constraint_name: 'C_VOLATILITY_COMPRESSION',
          contribution: 1.7,
          probability: 0.65,
          dominance_rank: 2,
        },
      ],
      friction_model: 'realistic',
    },
  },
  capital_tier: 'A',
  risk_budget: {
    today_consumed: 350,
    session_consumed: 150,
    trade_allocation: 100,
    max_daily: 1000,
  },
  active_template: 'K2',
  gates: [
    {
      gate_id: 'g_001',
      gate_name: 'GATE_EUC_POSITIVE',
      status: 'PASS',
      threshold_required: 0,
      current_value: 2.3,
      reason_codes: ['EUC_ABOVE_ZERO'],
      evidence: ['Edge contribution positive', 'Cost manageable'],
    },
    {
      gate_id: 'g_002',
      gate_name: 'GATE_FRICTION_TOO_HIGH',
      status: 'FAIL',
      threshold_required: 4.75,
      current_value: 6.20,
      reason_codes: ['GATE_FRICTION_TOO_HIGH', 'SPREAD_WIDENED'],
      evidence: ['Spread widened to 0.50', 'Slippage estimate high'],
    },
    {
      gate_id: 'g_003',
      gate_name: 'GATE_UNCERTAINTY_ACCEPTABLE',
      status: 'PASS',
      threshold_required: 5.0,
      current_value: 2.1,
      reason_codes: ['UNCERTAINTY_LOW'],
      evidence: ['Belief stability high', 'Evidence convergence strong'],
    },
  ],
  why_not: {
    primary_blocker: 'SKIP — Friction gate failed (required ≤ 4.75, current 6.20)',
    failed_gate: {
      gate_id: 'g_002',
      gate_name: 'GATE_FRICTION_TOO_HIGH',
      status: 'FAIL',
      threshold_required: 4.75,
      current_value: 6.20,
      reason_codes: ['GATE_FRICTION_TOO_HIGH', 'SPREAD_WIDENED'],
      evidence: ['Spread widened to 0.50', 'Slippage estimate high'],
    },
    what_would_change: 'Spread would need to tighten to ≤ 0.30, or friction model switched to optimistic',
    supporting_evidence: [
      'Current spread: 0.50 (avg: 0.25)',
      'Estimated slippage: 1.5 ticks',
      'Friction cost: 6.20 (threshold: 4.75)',
    ],
  },
  observed: {},
  believed: {},
};

export const mockSignals: Signal[] = Array.from({ length: 28 }, (_, i) => ({
  signal_id: `sig_${String(i + 1).padStart(3, '0')}`,
  signal_code: `S${i + 1}_${['RVOL_SPIKE', 'PRICE_MOMENTUM', 'STRUCTURE_BREAK', 'VOLUME_CLIMAX', 'REGIME_SHIFT'][i % 5]}`,
  signal_name: `Signal ${i + 1}`,
  category: ['MOMENTUM', 'VOLATILITY', 'STRUCTURE', 'FLOW', 'REGIME', 'TIME'][i % 6] as any,
  current_value: Math.random() * 100 - 50,
  reliability: 0.5 + Math.random() * 0.5,
  freshness_bars: Math.floor(Math.random() * 5),
  impact_on_decision: Math.random() * 10,
  status: ['OK', 'STALE', 'SUSPICIOUS'][Math.floor(Math.random() * 3)] as any,
  history: Array.from({ length: 50 }, () => Math.random() * 100 - 50),
}));

export const mockConstraints: Constraint[] = [
  {
    constraint_id: 'c_001',
    constraint_name: 'C_MOMENTUM_REGIME',
    probability: 0.78,
    stability: 0.92,
    dominance_rank: 1,
    decay_state: 0.95,
    applicability_gates: { session: true, regime: true, time: true },
  },
  {
    constraint_id: 'c_002',
    constraint_name: 'C_VOLATILITY_COMPRESSION',
    probability: 0.65,
    stability: 0.88,
    dominance_rank: 2,
    decay_state: 0.90,
    applicability_gates: { session: true, regime: true, time: false },
  },
  {
    constraint_id: 'c_003',
    constraint_name: 'C_STRUCTURE_STRENGTH',
    probability: 0.52,
    stability: 0.75,
    dominance_rank: 3,
    decay_state: 0.85,
    applicability_gates: { session: true, regime: false, time: true },
  },
];

export const mockBeliefStates: BeliefState[] = mockConstraints.map((c) => ({
  constraint_id: c.constraint_id,
  probability: c.probability,
  confidence: c.stability,
  stability_ewma: c.stability,
  evidence_for: ['Signal convergence strong', 'Historical pattern match'],
  evidence_against: ['Session volume low'],
  evidence_unknown: ['News impact unclear', 'Regime transition uncertain'],
  last_updated: new Date(Date.now() - Math.random() * 300000).toISOString(),
}));

export const mockExecutionQuality: ExecutionQuality = {
  dvs: 0.98,
  eqs: 0.95,
  modeled_friction: {
    realistic: 4.2,
    pessimistic: 6.8,
  },
  realized_friction: 4.5,
  slippage_delta: 0.3,
};

export const mockTrades: Trade[] = [
  {
    trade_id: 'trade_001',
    entry_time: new Date(Date.now() - 1800000).toISOString(),
    exit_time: new Date(Date.now() - 900000).toISOString(),
    pnl: 125.50,
    template: 'K2',
    fills: [
      {
        order_id: 'ord_001',
        type: 'ENTRY',
        sent_time: new Date(Date.now() - 1800000).toISOString(),
        fill_time: new Date(Date.now() - 1799000).toISOString(),
        expected_price: 4550.00,
        fill_price: 4550.25,
        slippage_ticks: 1,
        status: 'FILLED',
      },
      {
        order_id: 'ord_002',
        type: 'TARGET',
        sent_time: new Date(Date.now() - 900000).toISOString(),
        fill_time: new Date(Date.now() - 899000).toISOString(),
        expected_price: 4555.00,
        fill_price: 4555.00,
        slippage_ticks: 0,
        status: 'FILLED',
      },
    ],
    attribution: {
      classification: 'A2_GOOD_EDGE',
      edge_contribution: 80,
      luck_contribution: 15,
      execution_contribution: 5,
      learning_weight: 0.9,
      expected_outcome: {
        mean: 100,
        range: [50, 150],
      },
      realized_outcome: 125.50,
    },
  },
];

export const mockLearningUpdates: LearningUpdate[] = [
  {
    update_id: 'upd_001',
    timestamp: new Date(Date.now() - 600000).toISOString(),
    update_type: 'SIGNAL_RELIABILITY',
    before_value: 0.75,
    after_value: 0.82,
    reason_codes: ['SUCCESSFUL_PREDICTION', 'PATTERN_CONFIRMED'],
    triggering_events: ['evt_123', 'evt_124'],
    learning_weight: 0.9,
  },
  {
    update_id: 'upd_002',
    timestamp: new Date(Date.now() - 300000).toISOString(),
    update_type: 'CONSTRAINT_LIKELIHOOD',
    before_value: 0.65,
    after_value: 0.72,
    reason_codes: ['BELIEF_CONVERGENCE'],
    triggering_events: ['evt_125'],
    learning_weight: 0.85,
  },
];

export const mockConfigPatches: ConfigPatch[] = [
  {
    patch_id: 'patch_001',
    name: 'Reduce friction threshold',
    description: 'Lower friction gate threshold from 5.0 to 4.75 based on execution quality improvements',
    scope: ['gates', 'friction'],
    diff: { 'gates.friction.threshold': { from: 5.0, to: 4.75 } },
    safety_checks: {
      replay_tests_complete: true,
      invariants_passed: true,
      decision_delta_generated: true,
    },
    behavioral_impact: {
      decisions_changed_pct: 8.5,
      trades_added: 3,
      trades_removed: 1,
    },
  },
];

export const mockAlerts: Alert[] = [
  {
    alert_id: 'alert_001',
    timestamp: new Date(Date.now() - 120000).toISOString(),
    level: 'warning',
    category: 'BELIEF_DRIFT',
    message: 'Constraint C_MOMENTUM_REGIME drifting beyond allowed bounds',
    details: ['Probability changed by 15% in last 10 decisions', 'Stability EWMA declining'],
    dismissed: false,
  },
];
