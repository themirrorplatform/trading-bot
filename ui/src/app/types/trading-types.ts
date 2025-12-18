// Core data types for the trading bot cockpit

export type BotMode = 'OBSERVE' | 'PAPER' | 'LIVE';
export type KillSwitchState = 'ARMED' | 'TRIPPED';
export type Session = 'RTH' | 'ETH';
export type GateStatus = 'PASS' | 'FAIL' | 'NOT_APPLICABLE' | 'ERROR';
export type Severity = 'info' | 'warn' | 'bad' | 'good';
export type CapitalTier = 'S' | 'A' | 'B';
export type StrategyTemplate = 'K1' | 'K2' | 'K3' | 'K4' | null;

export interface Event {
  event_id: string;
  timestamp: string;
  event_type: EventType;
  severity: Severity;
  summary: string;
  payload: Record<string, any>;
  reason_codes: string[];
}

export type EventType = 
  | 'BAR_CLOSED'
  | 'SIGNALS_COMPUTED'
  | 'BELIEF_UPDATED'
  | 'DVS_EQS_UPDATED'
  | 'GATE_PASSED'
  | 'GATE_FAILED'
  | 'DECISION_MADE'
  | 'ORDER_SENT'
  | 'FILL'
  | 'EXIT'
  | 'ATTRIBUTION_V2'
  | 'LEARNING_UPDATE'
  | 'KILL_SWITCH_TRIPPED'
  | 'CONFIG_PATCH_APPLIED';

export interface DecisionRecord {
  decision_id: string;
  timestamp: string;
  outcome: 'TRADE' | 'SKIP' | 'HALT';
  euc: EUCScore;
  capital_tier: CapitalTier;
  risk_budget: RiskBudget;
  active_template: StrategyTemplate;
  proposed_order?: ProposedOrder;
  gates: GateResult[];
  why_not?: WhyNotRecord;
  observed: Record<string, any>;
  believed: Record<string, any>;
  expected_edge?: EdgeDistribution;
}

export interface EUCScore {
  total: number;
  edge: number;
  uncertainty: number;
  cost: number;
  breakdown: {
    constraint_contributions: ConstraintContribution[];
    friction_model: 'optimistic' | 'realistic' | 'pessimistic';
  };
}

export interface ConstraintContribution {
  constraint_id: string;
  constraint_name: string;
  contribution: number;
  probability: number;
  dominance_rank: number;
}

export interface RiskBudget {
  today_consumed: number;
  session_consumed: number;
  trade_allocation: number;
  max_daily: number;
}

export interface ProposedOrder {
  entry_price: number;
  stop_price: number;
  target_price: number;
  position_size: number;
  runner_logic?: string;
  time_stop?: string;
}

export interface GateResult {
  gate_id: string;
  gate_name: string;
  status: GateStatus;
  threshold_required?: number;
  current_value?: number;
  reason_codes: string[];
  evidence: string[];
}

export interface WhyNotRecord {
  primary_blocker: string;
  failed_gate: GateResult;
  what_would_change: string;
  supporting_evidence: string[];
}

export interface EdgeDistribution {
  expected_mean: number;
  uncertainty_range: [number, number];
  tail_risk: number;
}

export interface Signal {
  signal_id: string;
  signal_code: string;
  signal_name: string;
  category: SignalCategory;
  current_value: number;
  reliability: number;
  freshness_bars: number;
  impact_on_decision: number;
  status: 'OK' | 'STALE' | 'SUSPICIOUS';
  history: number[];
}

export type SignalCategory = 
  | 'MOMENTUM'
  | 'VOLATILITY'
  | 'STRUCTURE'
  | 'FLOW'
  | 'REGIME'
  | 'TIME';

export interface Constraint {
  constraint_id: string;
  constraint_name: string;
  probability: number;
  stability: number;
  dominance_rank: number;
  decay_state: number;
  applicability_gates: {
    session: boolean;
    regime: boolean;
    time: boolean;
  };
}

export interface BeliefState {
  constraint_id: string;
  probability: number;
  confidence: number;
  stability_ewma: number;
  evidence_for: string[];
  evidence_against: string[];
  evidence_unknown: string[];
  last_updated: string;
}

export interface ExecutionQuality {
  dvs: number; // Data Validity Score
  eqs: number; // Execution Quality Score
  modeled_friction: {
    realistic: number;
    pessimistic: number;
  };
  realized_friction?: number;
  slippage_delta?: number;
}

export interface Fill {
  order_id: string;
  type: 'ENTRY' | 'STOP' | 'TARGET' | 'EXIT';
  sent_time: string;
  fill_time?: string;
  expected_price: number;
  fill_price?: number;
  slippage_ticks?: number;
  status: 'PENDING' | 'PARTIAL' | 'FILLED' | 'CANCELLED';
}

export interface Trade {
  trade_id: string;
  entry_time: string;
  exit_time?: string;
  pnl?: number;
  attribution?: AttributionV2;
  template: StrategyTemplate;
  fills: Fill[];
}

export interface AttributionV2 {
  classification: AttributionClass;
  edge_contribution: number;
  luck_contribution: number;
  execution_contribution: number;
  learning_weight: number;
  expected_outcome: {
    mean: number;
    range: [number, number];
  };
  realized_outcome: number;
}

export type AttributionClass =
  | 'A0_LUCKY_WIN'
  | 'A1_BAD_MODEL'
  | 'A2_GOOD_EDGE'
  | 'A3_BAD_EXECUTION'
  | 'A4_TAIL_EVENT'
  | 'A5_LUCKY_LOSS';

export interface LearningUpdate {
  update_id: string;
  timestamp: string;
  update_type: LearningUpdateType;
  before_value: number;
  after_value: number;
  reason_codes: string[];
  triggering_events: string[];
  learning_weight: number;
}

export type LearningUpdateType =
  | 'SIGNAL_RELIABILITY'
  | 'CONSTRAINT_LIKELIHOOD'
  | 'DECAY_ADJUSTMENT'
  | 'GATE_THRESHOLD';

export interface ConfigPatch {
  patch_id: string;
  name: string;
  description: string;
  scope: string[];
  diff: Record<string, any>;
  safety_checks: {
    replay_tests_complete: boolean;
    invariants_passed: boolean;
    decision_delta_generated: boolean;
  };
  behavioral_impact: {
    decisions_changed_pct: number;
    trades_added: number;
    trades_removed: number;
  };
  applied_at?: string;
  applied_by?: string;
}

export interface Alert {
  alert_id: string;
  timestamp: string;
  level: 'critical' | 'warning' | 'info';
  category: string;
  message: string;
  details: string[];
  dismissed: boolean;
}

export interface MarketData {
  symbol: string;
  session: Session;
  last_price: number;
  change: number;
  change_pct: number;
  spread_proxy: number;
  volatility_proxy: number;
}

export interface SystemHealth {
  data_feed_uptime: number;
  latency_ms: number;
  missing_bars: number;
  clock_drift_ms: number;
  websocket_connected: boolean;
}
