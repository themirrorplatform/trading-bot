/**
 * Mock data for the Live Cockpit demonstration
 * Represents real-time trading bot decision states
 */

export const mockSystemState = {
  mode: 'PAPER' as const,
  session: 'RTH' as const,
  connectionStatus: 'LIVE' as const,
  killSwitch: {
    status: 'ARMED' as const,
    reason: undefined,
    timestamp: undefined,
    operator: undefined
  }
};

export const mockMarketData = {
  symbol: 'SPY',
  price: 452.38,
  change: 0.0042,
  volume: 54328900
};

// Current decision - SKIP example
export const mockSkipDecision = {
  type: 'SKIP' as const,
  timestamp: new Date().toISOString(),
  symbol: 'SPY',
  euc: {
    edge: 0.0023,
    uncertainty: 0.0018,
    cost: 0.0012,
    threshold: 0.0015,
    previous: -0.0002
  },
  capital: {
    tier: 'K2',
    allocated: 50000,
    riskBudget: 0.02
  },
  template: 'MEAN_REVERSION_SHORT',
  reasonCodes: ['INSUFFICIENT_EUC', 'VOL_REGIME_MISMATCH', 'POSITION_SIZE_CONSTRAINED']
};

// Current decision - TRADE example
export const mockTradeDecision = {
  type: 'TRADE' as const,
  timestamp: new Date().toISOString(),
  symbol: 'SPY',
  direction: 'LONG' as const,
  euc: {
    edge: 0.0038,
    uncertainty: 0.0011,
    cost: 0.0008,
    threshold: 0.0015,
    previous: 0.0012
  },
  capital: {
    tier: 'K3',
    allocated: 100000,
    riskBudget: 0.03
  },
  template: 'MOMENTUM_LONG',
  expectedOutcome: {
    probability: 0.64,
    expectedValue: 285.50,
    timeHorizon: '2-4 hours'
  },
  reasonCodes: ['STRONG_MOMENTUM', 'VOL_COMPRESSION', 'LIQUIDITY_SUFFICIENT']
};

// Current decision - HALT example
export const mockHaltDecision = {
  type: 'HALT' as const,
  timestamp: new Date().toISOString(),
  symbol: 'SPY',
  euc: {
    edge: 0.0001,
    uncertainty: 0.0045,
    cost: 0.0009,
    threshold: 0.0015,
    previous: 0.0018
  },
  capital: {
    tier: 'K1',
    allocated: 0,
    riskBudget: 0
  },
  template: 'NONE',
  reasonCodes: ['UNCERTAINTY_SPIKE', 'DATA_QUALITY_DEGRADED', 'OPERATOR_PAUSE']
};

export const mockEvents = [
  {
    id: 'evt_001',
    timestamp: new Date(Date.now() - 1000 * 30).toISOString(),
    type: 'DECISION',
    severity: 'INFO' as const,
    summary: 'Trade opportunity evaluated: SKIP decision (insufficient EUC)',
    details: {
      reasonCodes: ['INSUFFICIENT_EUC', 'VOL_REGIME_MISMATCH'],
      inputs: { euc: 0.0005, threshold: 0.0015, volatility: 0.18 },
      outputs: { decision: 'SKIP', confidence: 0.89 }
    }
  },
  {
    id: 'evt_002',
    timestamp: new Date(Date.now() - 1000 * 45).toISOString(),
    type: 'SIGNAL_UPDATE',
    severity: 'INFO' as const,
    summary: 'Momentum signal updated: 0.0234 → 0.0189 (reliability: 0.87)',
    details: {
      reasonCodes: ['SIGNAL_DECAY'],
      inputs: { previous: 0.0234, current: 0.0189 }
    }
  },
  {
    id: 'evt_003',
    timestamp: new Date(Date.now() - 1000 * 62).toISOString(),
    type: 'GATE_EVAL',
    severity: 'WARNING' as const,
    summary: 'Gate evaluation: Minimum liquidity FAIL (required: 1M, actual: 780K)',
    details: {
      reasonCodes: ['LIQUIDITY_BELOW_THRESHOLD'],
      inputs: { required: 1000000, actual: 780000 }
    }
  },
  {
    id: 'evt_004',
    timestamp: new Date(Date.now() - 1000 * 85).toISOString(),
    type: 'DECISION',
    severity: 'INFO' as const,
    summary: 'Trade opportunity evaluated: SKIP decision (position limits)',
    details: {
      reasonCodes: ['POSITION_LIMIT_REACHED'],
      inputs: { currentPositions: 5, maxPositions: 5 }
    }
  },
  {
    id: 'evt_005',
    timestamp: new Date(Date.now() - 1000 * 120).toISOString(),
    type: 'CONSTRAINT',
    severity: 'INFO' as const,
    summary: 'Constraint update: Mean reversion belief probability 0.68 → 0.71',
    details: {
      reasonCodes: ['BELIEF_STRENGTHENED'],
      inputs: { previous: 0.68, current: 0.71, evidence: 'price_mean_distance' }
    }
  },
  {
    id: 'evt_006',
    timestamp: new Date(Date.now() - 1000 * 145).toISOString(),
    type: 'EXECUTION',
    severity: 'INFO' as const,
    summary: 'Order filled: 100 shares @ $452.12 (slippage: -$0.03)',
    details: {
      reasonCodes: ['FULL_FILL'],
      inputs: { expectedPrice: 452.15, fillPrice: 452.12, shares: 100 }
    }
  },
  {
    id: 'evt_007',
    timestamp: new Date(Date.now() - 1000 * 180).toISOString(),
    type: 'LEARNING',
    severity: 'INFO' as const,
    summary: 'Learning update applied: Momentum signal normalization adjusted',
    details: {
      reasonCodes: ['ATTRIBUTION_FEEDBACK'],
      inputs: { learningWeight: 0.05, oldParam: 1.2, newParam: 1.25 }
    }
  },
  {
    id: 'evt_008',
    timestamp: new Date(Date.now() - 1000 * 210).toISOString(),
    type: 'HEALTH',
    severity: 'WARNING' as const,
    summary: 'Data feed latency spike: 45ms → 125ms',
    details: {
      reasonCodes: ['LATENCY_DEGRADATION'],
      inputs: { baseline: 45, current: 125, threshold: 100 }
    }
  }
];

export const mockLiveGates = [
  {
    name: 'Minimum EUC',
    status: 'FAIL' as const,
    required: 0.0015,
    actual: 0.0005,
    reasonCode: 'EUC_BELOW_THRESHOLD'
  },
  {
    name: 'Maximum Position Size',
    status: 'PASS' as const,
    required: 5,
    actual: 3,
    reasonCode: 'WITHIN_LIMITS'
  },
  {
    name: 'Minimum Liquidity',
    status: 'FAIL' as const,
    required: 1000000,
    actual: 780000,
    reasonCode: 'LIQUIDITY_LOW'
  },
  {
    name: 'Volatility Regime Match',
    status: 'FAIL' as const,
    required: 0.15,
    actual: 0.18,
    unit: '',
    reasonCode: 'VOL_MISMATCH'
  },
  {
    name: 'Signal Reliability',
    status: 'PASS' as const,
    required: 0.70,
    actual: 0.87,
    unit: '',
    reasonCode: 'RELIABLE'
  },
  {
    name: 'Risk Budget Available',
    status: 'PASS' as const,
    required: 0.01,
    actual: 0.08,
    unit: '',
    reasonCode: 'BUDGET_OK'
  },
  {
    name: 'Time in Market Session',
    status: 'PASS' as const,
    required: 1,
    actual: 1,
    reasonCode: 'RTH_ACTIVE'
  },
  {
    name: 'Correlation Limits',
    status: 'PASS' as const,
    required: 0.80,
    actual: 0.45,
    unit: '',
    reasonCode: 'LOW_CORRELATION'
  }
];

export const mockBlockingGates = [
  {
    name: 'Minimum EUC',
    status: 'FAIL' as const,
    required: 0.0015,
    actual: 0.0005,
    reasonCode: 'EUC_BELOW_THRESHOLD',
    reasonDescription: 'Net expected utility below required threshold for trade execution'
  },
  {
    name: 'Minimum Liquidity',
    status: 'FAIL' as const,
    required: 1000000,
    actual: 780000,
    reasonCode: 'LIQUIDITY_LOW',
    reasonDescription: 'Current market liquidity below minimum for safe execution'
  },
  {
    name: 'Volatility Regime Match',
    status: 'FAIL' as const,
    required: 0.15,
    actual: 0.18,
    reasonCode: 'VOL_MISMATCH',
    reasonDescription: 'Current volatility outside of template\'s optimal regime'
  }
];

export const mockWhatWouldChange = [
  'EUC needs to increase by +0.0010 (currently 0.0005, required 0.0015)',
  'Market liquidity needs to increase by 220K shares (currently 780K, required 1M)',
  'Volatility needs to decrease to ≤0.15 (currently 0.18)'
];

// Additional state configurations for edge cases
export const mockSystemStateDisconnected = {
  mode: 'PAPER' as const,
  session: 'RTH' as const,
  connectionStatus: 'DISCONNECTED' as const,
  killSwitch: {
    status: 'ARMED' as const,
    reason: undefined,
    timestamp: undefined,
    operator: undefined
  }
};

export const mockSystemStateKillSwitch = {
  mode: 'LIVE' as const,
  session: 'RTH' as const,
  connectionStatus: 'LIVE' as const,
  killSwitch: {
    status: 'TRIPPED' as const,
    reason: 'Consecutive losing trades exceeded threshold',
    timestamp: new Date(Date.now() - 1000 * 120).toISOString(),
    operator: 'AUTO_RISK_MANAGER'
  }
};

// Alternative gate configurations
export const mockLiveGatesAllPass = [
  {
    name: 'Minimum EUC',
    status: 'PASS' as const,
    required: 0.0015,
    actual: 0.0038,
    reasonCode: 'EUC_SUFFICIENT'
  },
  {
    name: 'Maximum Position Size',
    status: 'PASS' as const,
    required: 5,
    actual: 3,
    reasonCode: 'WITHIN_LIMITS'
  },
  {
    name: 'Minimum Liquidity',
    status: 'PASS' as const,
    required: 1000000,
    actual: 2500000,
    reasonCode: 'LIQUIDITY_OK'
  },
  {
    name: 'Volatility Regime Match',
    status: 'PASS' as const,
    required: 0.15,
    actual: 0.12,
    reasonCode: 'VOL_MATCHED'
  },
  {
    name: 'Signal Reliability',
    status: 'PASS' as const,
    required: 0.70,
    actual: 0.92,
    reasonCode: 'HIGHLY_RELIABLE'
  },
  {
    name: 'Risk Budget Available',
    status: 'PASS' as const,
    required: 0.01,
    actual: 0.12,
    reasonCode: 'BUDGET_OK'
  },
  {
    name: 'Time in Market Session',
    status: 'PASS' as const,
    required: 1,
    actual: 1,
    reasonCode: 'RTH_ACTIVE'
  },
  {
    name: 'Correlation Limits',
    status: 'PASS' as const,
    required: 0.80,
    actual: 0.35,
    reasonCode: 'LOW_CORRELATION'
  }
];