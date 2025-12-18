import React from 'react';
import { cn } from '../components/ui/utils';
import { ReasonCodeChip } from '../components/ReasonCodeChip';
import { StatusBadge } from '../components/StatusBadge';
import { ScrollArea } from '../components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';
import type { LearningUpdate, Alert } from '../types/trading-types';

interface LearningConsoleProps {
  learningUpdates: LearningUpdate[];
  alerts: Alert[];
}

export function LearningConsole({ learningUpdates, alerts }: LearningConsoleProps) {
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', { 
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  };

  const getUpdateTypeColor = (type: string) => {
    switch (type) {
      case 'SIGNAL_RELIABILITY': return 'info';
      case 'CONSTRAINT_LIKELIHOOD': return 'accent';
      case 'DECAY_ADJUSTMENT': return 'warn';
      case 'GATE_THRESHOLD': return 'neutral';
      default: return 'neutral';
    }
  };

  const getAlertLevelColor = (level: string) => {
    switch (level) {
      case 'critical': return 'bad';
      case 'warning': return 'warn';
      case 'info': return 'info';
      default: return 'neutral';
    }
  };

  return (
    <div className="h-full p-6 space-y-6">
      {/* Header */}
      <div>
        <h2 className="font-semibold text-[#E7EEF9] mb-1">Learning Console</h2>
        <p className="text-sm text-[#7F93B2]">What's changing, how fast, and why</p>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="updates" className="w-full">
        <TabsList className="bg-[#111826] border border-[#22304A]">
          <TabsTrigger value="updates">Recent Updates</TabsTrigger>
          <TabsTrigger value="drift">Drift & Stability</TabsTrigger>
          <TabsTrigger value="alerts">Alerts ({alerts.filter(a => !a.dismissed).length})</TabsTrigger>
        </TabsList>

        {/* Recent Updates Tab */}
        <TabsContent value="updates" className="space-y-4 mt-6">
          <div className="bg-[#111826] border border-[#22304A] rounded-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-[#22304A]">
              <h3 className="font-medium text-[#E7EEF9]">Recent Learning Updates</h3>
              <p className="text-sm text-[#7F93B2] mt-1">Last {learningUpdates.length} updates</p>
            </div>

            <ScrollArea className="h-[600px]">
              <div className="p-6 space-y-4">
                {learningUpdates.map((update) => {
                  const isIncrease = update.after_value > update.before_value;
                  const delta = update.after_value - update.before_value;
                  const deltaPercent = ((delta / update.before_value) * 100).toFixed(1);

                  return (
                    <div
                      key={update.update_id}
                      className="bg-[#162033] border border-[#22304A] rounded-lg p-4 space-y-3"
                    >
                      {/* Header */}
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <StatusBadge status={getUpdateTypeColor(update.update_type) as any}>
                              {update.update_type.replace(/_/g, ' ')}
                            </StatusBadge>
                            <div className="text-xs text-[#7F93B2]">
                              {formatTime(update.timestamp)}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {isIncrease ? (
                            <TrendingUp className="w-4 h-4 text-[#2ED47A]" />
                          ) : (
                            <TrendingDown className="w-4 h-4 text-[#FF5A5F]" />
                          )}
                        </div>
                      </div>

                      {/* Value Change */}
                      <div className="flex items-center gap-4">
                        <div className="flex-1">
                          <div className="text-xs text-[#7F93B2] mb-1">Before → After</div>
                          <div className="flex items-center gap-3 text-sm">
                            <span className="text-[#B8C7E0] font-mono tabular-nums">
                              {update.before_value.toFixed(3)}
                            </span>
                            <span className="text-[#7F93B2]">→</span>
                            <span className="text-[#E7EEF9] font-mono tabular-nums">
                              {update.after_value.toFixed(3)}
                            </span>
                            <span className={cn(
                              'px-2 py-0.5 rounded text-xs font-mono tabular-nums',
                              isIncrease ? 'bg-[#1A7A45] text-[#2ED47A]' : 'bg-[#8B2C2F] text-[#FF5A5F]'
                            )}>
                              {isIncrease ? '+' : ''}{deltaPercent}%
                            </span>
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-[#7F93B2] mb-1">Learning Weight</div>
                          <div className="text-sm text-[#E7EEF9] font-mono tabular-nums">
                            {(update.learning_weight * 100).toFixed(0)}%
                          </div>
                        </div>
                      </div>

                      {/* Reason Codes */}
                      {update.reason_codes.length > 0 && (
                        <div>
                          <div className="text-xs text-[#7F93B2] mb-2">Reason Codes</div>
                          <div className="flex flex-wrap gap-2">
                            {update.reason_codes.map((code, i) => (
                              <ReasonCodeChip key={i} code={code} />
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Triggering Events */}
                      {update.triggering_events.length > 0 && (
                        <div className="pt-3 border-t border-[#22304A]">
                          <div className="text-xs text-[#7F93B2] mb-2">Triggering Events</div>
                          <div className="flex flex-wrap gap-2">
                            {update.triggering_events.map((eventId, i) => (
                              <button
                                key={i}
                                className="px-2 py-1 bg-[#111826] border border-[#22304A] rounded text-xs font-mono text-[#4DA3FF] hover:border-[#4DA3FF] transition-colors"
                              >
                                {eventId}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* What Changed */}
                      <div className="text-xs text-[#B8C7E0] bg-[#111826] p-3 rounded">
                        Update applied based on {update.reason_codes[0] || 'learning rule'}.
                        Confidence: {(update.learning_weight * 100).toFixed(0)}%.
                      </div>
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          </div>
        </TabsContent>

        {/* Drift & Stability Tab */}
        <TabsContent value="drift" className="space-y-4 mt-6">
          <div className="grid grid-cols-2 gap-6">
            {/* Belief Drift Chart */}
            <div className="bg-[#111826] border border-[#22304A] rounded-xl p-6">
              <h3 className="font-medium text-[#E7EEF9] mb-4">Belief Drift</h3>
              <div className="h-64 flex items-center justify-center">
                <svg width="100%" height="100%" viewBox="0 0 400 200" className="overflow-visible">
                  {/* Grid */}
                  {[0, 50, 100, 150, 200].map((y) => (
                    <line
                      key={y}
                      x1="0"
                      y1={y}
                      x2="400"
                      y2={y}
                      stroke="#22304A"
                      strokeWidth="1"
                      strokeDasharray="2,2"
                    />
                  ))}
                  
                  {/* Bounds */}
                  <line x1="0" y1="40" x2="400" y2="40" stroke="#FFB020" strokeWidth="1" strokeDasharray="4,4" />
                  <line x1="0" y1="160" x2="400" y2="160" stroke="#FFB020" strokeWidth="1" strokeDasharray="4,4" />
                  
                  {/* Drift Line */}
                  <polyline
                    fill="none"
                    stroke="#B38BFF"
                    strokeWidth="2"
                    points="0,100 80,105 160,95 240,110 320,115 400,108"
                  />
                </svg>
              </div>
              <div className="text-xs text-[#7F93B2] text-center mt-2">
                Probability drift over last 50 decisions
              </div>
            </div>

            {/* Stability Metrics */}
            <div className="bg-[#111826] border border-[#22304A] rounded-xl p-6">
              <h3 className="font-medium text-[#E7EEF9] mb-4">Stability Metrics</h3>
              <div className="space-y-4">
                <div className="p-4 bg-[#162033] rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-[#E7EEF9]">Belief Instability</span>
                    <span className="text-xs px-2 py-1 bg-[#1A7A45] text-[#2ED47A] rounded">STABLE</span>
                  </div>
                  <div className="text-2xl font-semibold text-[#E7EEF9] tabular-nums">
                    0.08
                  </div>
                  <div className="text-xs text-[#7F93B2] mt-1">Below threshold (0.15)</div>
                </div>

                <div className="p-4 bg-[#162033] rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-[#E7EEF9]">Overconfidence Score</span>
                    <span className="text-xs px-2 py-1 bg-[#1A7A45] text-[#2ED47A] rounded">HEALTHY</span>
                  </div>
                  <div className="text-2xl font-semibold text-[#E7EEF9] tabular-nums">
                    0.12
                  </div>
                  <div className="text-xs text-[#7F93B2] mt-1">Within bounds (0.0 - 0.25)</div>
                </div>

                <div className="p-4 bg-[#162033] rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-[#E7EEF9]">Signal Reliability Runaway</span>
                    <span className="text-xs px-2 py-1 bg-[#1A7A45] text-[#2ED47A] rounded">NONE</span>
                  </div>
                  <div className="text-sm text-[#7F93B2] mt-2">
                    No signals showing runaway patterns
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Gate Saturation Detector */}
          <div className="bg-[#111826] border border-[#22304A] rounded-xl p-6">
            <h3 className="font-medium text-[#E7EEF9] mb-4">Gate Saturation Detector</h3>
            <div className="space-y-3">
              <div className="p-3 bg-[#1A7A45]/10 border border-[#2ED47A]/20 rounded text-sm text-[#2ED47A]">
                ✓ No gates showing saturation patterns
              </div>
              <div className="text-xs text-[#7F93B2]">
                Monitors for gates that consistently block decisions (saturation) or never trigger (underutilization)
              </div>
            </div>
          </div>
        </TabsContent>

        {/* Alerts Tab */}
        <TabsContent value="alerts" className="space-y-4 mt-6">
          <div className="bg-[#111826] border border-[#22304A] rounded-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-[#22304A]">
              <h3 className="font-medium text-[#E7EEF9]">Active Alerts</h3>
            </div>

            <ScrollArea className="h-[600px]">
              <div className="p-6 space-y-4">
                {alerts.filter(a => !a.dismissed).length === 0 ? (
                  <div className="text-center py-12 text-[#7F93B2]">
                    No active alerts
                  </div>
                ) : (
                  alerts.filter(a => !a.dismissed).map((alert) => (
                    <div
                      key={alert.alert_id}
                      className={cn(
                        'border rounded-lg p-4 space-y-3',
                        alert.level === 'critical' && 'bg-[#8B2C2F]/10 border-[#FF5A5F]/20',
                        alert.level === 'warning' && 'bg-[#8B5A00]/10 border-[#FFB020]/20',
                        alert.level === 'info' && 'bg-[#285A8F]/10 border-[#4DA3FF]/20'
                      )}
                    >
                      {/* Header */}
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-center gap-3">
                          <AlertTriangle className={cn(
                            'w-5 h-5',
                            alert.level === 'critical' && 'text-[#FF5A5F]',
                            alert.level === 'warning' && 'text-[#FFB020]',
                            alert.level === 'info' && 'text-[#4DA3FF]'
                          )} />
                          <div>
                            <StatusBadge status={getAlertLevelColor(alert.level) as any}>
                              {alert.level.toUpperCase()}
                            </StatusBadge>
                            <div className="text-xs text-[#7F93B2] mt-1">
                              {formatTime(alert.timestamp)}
                            </div>
                          </div>
                        </div>
                        <button className="px-3 py-1 bg-[#162033] text-[#B8C7E0] border border-[#22304A] rounded text-xs hover:border-[#B38BFF] transition-colors">
                          Dismiss
                        </button>
                      </div>

                      {/* Category & Message */}
                      <div>
                        <div className="text-xs text-[#7F93B2] mb-1">{alert.category}</div>
                        <div className={cn(
                          'text-sm font-medium',
                          alert.level === 'critical' && 'text-[#FF5A5F]',
                          alert.level === 'warning' && 'text-[#FFB020]',
                          alert.level === 'info' && 'text-[#4DA3FF]'
                        )}>
                          {alert.message}
                        </div>
                      </div>

                      {/* Details */}
                      {alert.details.length > 0 && (
                        <div className="space-y-1 pt-2 border-t border-[#22304A]">
                          {alert.details.map((detail, i) => (
                            <div key={i} className="text-xs text-[#B8C7E0]">
                              • {detail}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
