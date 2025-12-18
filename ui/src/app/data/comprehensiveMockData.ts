/**
 * Comprehensive Mock Data - ALL event types, beliefs, attributions, manual actions
 * Represents complete epistemic transparency
 */

// Belief States
export const mockBeliefs = [
  {
    name: 'Mean Reversion Active',
    probability: 0.72,
    stability: 0.85,
    decayState: 'ACTIVE' as const,
    applicabilityGates: [
      { name: 'Price Distance', status: 'PASS' as const },
      { name: 'Vol Regime', status: 'PASS' as const }
    ],
    evidenceFor: 0.65,
    evidenceAgainst: 0.15,
    evidenceUnknown: 0.20,
    lastUpdate: new Date(Date.now() - 1000 * 45).toISOString()
  },
  {
    name: 'Momentum Exhaustion',
    probability: 0.38,
    stability: 0.62,
    decayState: 'DECAYING' as const,
    applicabilityGates: [
      { name: 'Momentum Duration', status: 'FAIL' as const },
      { name: 'Volume Profile', status: 'PASS' as const }
    ],
    evidenceFor: 0.40,
    evidenceAgainst: 0.45,
    evidenceUnknown: 0.15,
    lastUpdate: new Date(Date.now() - 1000 * 120).toISOString()
  },
  {
    name: 'High Volatility Regime',
    probability: 0.18,
    stability: 0.45,
    decayState: 'STALE' as const,
    applicabilityGates: [
      { name: 'Vol Threshold', status: 'FAIL' as const }
    ],
    evidenceFor: 0.20,
    evidenceAgainst: 0.60,
    evidenceUnknown: 0.20,
    lastUpdate: new Date(Date.now() - 1000 * 300).toISOString()
  }
];

// Complete Event Timeline with ALL types
export const mockCompleteEvents = [
  {
    id: 'evt_bar_001',
    timestamp: new Date(Date.now() - 1000 * 5).toISOString(),
    type: 'BAR_CLOSE' as const,
    severity: 'INFO' as const,
    summary: 'SPY 1min bar closed: O:452.38 H:452.45 L:452.32 C:452.40',
    details: {
      reasonCodes: ['BAR_COMPLETE'],
      inputs: { open: 452.38, high: 452.45, low: 452.32, close: 452.40, volume: 125000 }
    }
  },
  {
    id: 'evt_decision_001',
    timestamp: new Date(Date.now() - 1000 * 10).toISOString(),
    type: 'DECISION' as const,
    severity: 'INFO' as const,
    summary: 'Trade opportunity evaluated: SKIP decision (insufficient EUC)',
    details: {
      reasonCodes: ['INSUFFICIENT_EUC', 'VOL_REGIME_MISMATCH'],
      inputs: { euc: 0.0005, threshold: 0.0015, volatility: 0.18 },
      outputs: { decision: 'SKIP', confidence: 0.89 }
    }
  },
  {
    id: 'evt_order_001',
    timestamp: new Date(Date.now() - 1000 * 150).toISOString(),
    type: 'ORDER_SUBMIT' as const,
    severity: 'INFO' as const,
    summary: 'Order submitted: BUY 100 SPY @ 452.15 LIMIT',
    details: {
      reasonCodes: ['ORDER_PLACED'],
      inputs: { symbol: 'SPY', qty: 100, side: 'BUY', orderType: 'LIMIT', limitPrice: 452.15 }
    }
  },
  {
    id: 'evt_fill_001',
    timestamp: new Date(Date.now() - 1000 * 145).toISOString(),
    type: 'FILL' as const,
    severity: 'INFO' as const,
    summary: 'Order filled: 100 shares @ $452.12 (slippage: -$0.03)',
    details: {
      reasonCodes: ['FULL_FILL'],
      inputs: { expectedPrice: 452.15, fillPrice: 452.12, shares: 100, slippage: -0.03 },
      outputs: { fillType: 'FULL', executionQuality: 0.92 }
    }
  },
  {
    id: 'evt_exit_001',
    timestamp: new Date(Date.now() - 1000 * 90).toISOString(),
    type: 'EXIT' as const,
    severity: 'INFO' as const,
    summary: 'Position closed: 100 SPY @ $452.68 (PnL: +$56)',
    details: {
      reasonCodes: ['TARGET_HIT', 'EXIT_SIGNAL'],
      inputs: { entryPrice: 452.12, exitPrice: 452.68, qty: 100 },
      outputs: { pnl: 56, holdTime: '55s' }
    }
  },
  {
    id: 'evt_attribution_001',
    timestamp: new Date(Date.now() - 1000 * 85).toISOString(),
    type: 'ATTRIBUTION' as const,
    severity: 'INFO' as const,
    summary: 'Attribution complete: Edge +$42, Luck +$18, Execution -$4',
    details: {
      reasonCodes: ['ATTRIBUTION_V2'],
      inputs: { totalPnL: 56, expectedPnL: 38 },
      outputs: { edge: 42, luck: 18, execution: -4, learningWeight: 0.85 }
    }
  },
  {
    id: 'evt_learning_001',
    timestamp: new Date(Date.now() - 1000 * 80).toISOString(),
    type: 'LEARNING' as const,
    severity: 'INFO' as const,
    summary: 'Learning update applied: Momentum signal normalization adjusted',
    details: {
      reasonCodes: ['ATTRIBUTION_FEEDBACK', 'EDGE_CONFIRMED'],
      inputs: { learningWeight: 0.85, oldParam: 1.2, newParam: 1.22 },
      outputs: { parameterUpdated: 'momentum_norm', confidence: 0.87 }
    }
  },
  {
    id: 'evt_constraint_001',
    timestamp: new Date(Date.now() - 1000 * 120).toISOString(),
    type: 'CONSTRAINT' as const,
    severity: 'INFO' as const,
    summary: 'Constraint update: Mean reversion belief probability 0.68 → 0.72',
    details: {
      reasonCodes: ['BELIEF_STRENGTHENED', 'EVIDENCE_ACCUMULATED'],
      inputs: { previous: 0.68, current: 0.72, evidence: 'price_mean_distance', stability: 0.85 }
    }
  },
  {
    id: 'evt_gate_001',
    timestamp: new Date(Date.now() - 1000 * 62).toISOString(),
    type: 'GATE_EVAL' as const,
    severity: 'WARNING' as const,
    summary: 'Gate evaluation: Minimum liquidity FAIL (required: 1M, actual: 780K)',
    details: {
      reasonCodes: ['LIQUIDITY_BELOW_THRESHOLD'],
      inputs: { required: 1000000, actual: 780000, gate: 'min_liquidity' }
    }
  },
  {
    id: 'evt_health_001',
    timestamp: new Date(Date.now() - 1000 * 210).toISOString(),
    type: 'HEALTH' as const,
    severity: 'WARNING' as const,
    summary: 'Data feed latency spike: 45ms → 125ms',
    details: {
      reasonCodes: ['LATENCY_DEGRADATION'],
      inputs: { baseline: 45, current: 125, threshold: 100, feed: 'market_data' }
    }
  },
  {
    id: 'evt_signal_001',
    timestamp: new Date(Date.now() - 1000 * 45).toISOString(),
    type: 'SIGNAL_UPDATE' as const,
    severity: 'INFO' as const,
    summary: 'Momentum signal updated: 0.0234 → 0.0189 (reliability: 0.87)',
    details: {
      reasonCodes: ['SIGNAL_DECAY', 'NORMAL_UPDATE'],
      inputs: { previous: 0.0234, current: 0.0189, reliability: 0.87 }
    }
  }
];

// Drift Alerts
export const mockDriftAlerts = [
  {
    type: 'BELIEF_DRIFT' as const,
    severity: 'WARNING' as const,
    message: 'Mean reversion belief showing drift from baseline',
    details: 'Probability has shifted from 0.58 → 0.72 over 2 hours without corresponding market regime change',
    detectedAt: new Date(Date.now() - 1000 * 300).toISOString(),
    affectedComponents: ['mean_reversion_short', 'K2_templates'],
    recommendedAction: 'Monitor next 10 decisions for confirmation bias'
  },
  {
    type: 'GATE_SATURATION' as const,
    severity: 'WARNING' as const,
    message: 'Risk budget gate approaching saturation',
    details: 'Gate has been at 95%+ capacity for last 15 minutes, limiting trade opportunities',
    detectedAt: new Date(Date.now() - 1000 * 180).toISOString(),
    affectedComponents: ['risk_budget_gate', 'all_templates'],
    recommendedAction: 'Consider adjusting risk budget threshold or reviewing position sizes'
  }
];

// Manual Actions
export const mockManualActions = [
  {
    id: 'action_001',
    type: 'PAUSE' as const,
    operator: 'John Smith',
    timestamp: new Date(Date.now() - 1000 * 600).toISOString(),
    reason: 'Elevated volatility spike, pausing to observe',
    details: { previousMode: 'PAPER', pauseDuration: 'indefinite' },
    impactedDecisions: ['decision_123', 'decision_124']
  },
  {
    id: 'action_002',
    type: 'RESUME' as const,
    operator: 'John Smith',
    timestamp: new Date(Date.now() - 1000 * 300).toISOString(),
    reason: 'Volatility normalized, resuming paper trading',
    details: { newMode: 'PAPER' }
  },
  {
    id: 'action_003',
    type: 'ANNOTATION' as const,
    operator: 'Jane Doe',
    timestamp: new Date(Date.now() - 1000 * 200).toISOString(),
    reason: 'Note on mean reversion performance',
    details: { 
      linkedTo: 'trade_456',
      note: 'This trade executed during low liquidity period - exclude from learning'
    }
  }
];

// Annotations
export const mockAnnotations = [
  {
    id: 'annotation_001',
    linkedTo: { type: 'TRADE' as const, id: 'trade_456' },
    text: 'Executed during low liquidity window (ETH transition). Exclude from learning to avoid biasing model against otherwise good signals.',
    author: 'Jane Doe',
    timestamp: new Date(Date.now() - 1000 * 200).toISOString(),
    tags: ['low_liquidity', 'exclude_learning', 'eth_transition']
  },
  {
    id: 'annotation_002',
    linkedTo: { type: 'EVENT' as const, id: 'evt_decision_001' },
    text: 'SKIP was correct - price reversed immediately after. Good gate failure.',
    author: 'John Smith',
    timestamp: new Date(Date.now() - 1000 * 100).toISOString(),
    tags: ['correct_skip', 'gates_working']
  }
];

// Attribution Example
export const mockAttribution = {
  tradeId: 'trade_456',
  closedAt: new Date(Date.now() - 1000 * 85).toISOString(),
  totalPnL: 56,
  edgeContribution: 42,
  luckContribution: 18,
  executionContribution: -4,
  learningWeight: 0.85,
  expectedPnL: 38,
  realizedPnL: 56,
  classification: 'EDGE_WIN' as const
};

// Execution Blame
export const mockExecutionBlame = {
  tradeId: 'trade_456',
  expectedFillPrice: 452.15,
  realizedFillPrice: 452.12,
  expectedSlippage: 0.0005,
  realizedSlippage: -0.0003,
  strategyQuality: 0.72,
  executionQuality: -0.15,
  marketNoise: 0.25,
  fillType: 'FULL' as const
};

// Data Quality
export const mockDataQuality = [
  {
    feedName: 'Market Data (Primary)',
    status: 'HEALTHY' as const,
    latency: { current: 12, baseline: 10, threshold: 50 },
    missingBars: { count: 0, lastMissing: '' },
    dataFreshness: 0.5,
    errorRate: 0.001
  },
  {
    feedName: 'Options Data',
    status: 'DEGRADED' as const,
    latency: { current: 125, baseline: 45, threshold: 100 },
    missingBars: { count: 2, lastMissing: new Date(Date.now() - 1000 * 210).toISOString() },
    dataFreshness: 3.2,
    errorRate: 0.05
  }
];

// Live Gates - All Pass (for TRADE decision)
export const mockLiveGatesAllPass = [
  {
    name: 'Minimum EUC',
    status: 'PASS' as const,
    required: 0.0015,
    actual: 0.0042,
    reasonCode: 'EUC_ABOVE_THRESHOLD'
  },
  {
    name: 'Maximum Position Size',
    status: 'PASS' as const,
    required: 5,
    actual: 3,
    reasonCode: 'WITHIN_LIMITS'
  },
  {
    name: 'Risk Budget Available',
    status: 'PASS' as const,
    required: 0.01,
    actual: 0.015,
    reasonCode: 'BUDGET_AVAILABLE'
  },
  {
    name: 'Minimum Liquidity',
    status: 'PASS' as const,
    required: 1000000,
    actual: 1250000,
    reasonCode: 'LIQUIDITY_ADEQUATE'
  },
  {
    name: 'Market Hours',
    status: 'PASS' as const,
    required: 1,
    actual: 1,
    reasonCode: 'RTH_ACTIVE'
  },
  {
    name: 'Volatility Regime',
    status: 'PASS' as const,
    required: 0.25,
    actual: 0.18,
    reasonCode: 'VOL_WITHIN_RANGE'
  },
  {
    name: 'Kill Switch',
    status: 'PASS' as const,
    required: 1,
    actual: 1,
    reasonCode: 'KILL_SWITCH_ARMED'
  },
  {
    name: 'Data Quality',
    status: 'PASS' as const,
    required: 0.95,
    actual: 0.99,
    reasonCode: 'DATA_HEALTHY'
  }
];