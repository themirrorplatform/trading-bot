/**
 * ManualActionLog - Shows all operator interventions
 * Critical for governance and auditability
 */

import { Card } from '../primitives/Card';
import { Timestamp } from '../primitives/Timestamp';
import { Badge } from '../primitives/Badge';

interface ManualAction {
  id: string;
  type: 'PAUSE' | 'RESUME' | 'FLATTEN' | 'OVERRIDE' | 'EMERGENCY_HALT' | 'PARAMETER_CHANGE' | 'ANNOTATION';
  operator: string;
  timestamp: string;
  reason: string;
  details?: Record<string, any>;
  impactedDecisions?: string[];
}

interface ManualActionLogProps {
  actions: ManualAction[];
  maxVisible?: number;
  className?: string;
}

export function ManualActionLog({ actions, maxVisible = 10, className = '' }: ManualActionLogProps) {
  const visibleActions = maxVisible ? actions.slice(0, maxVisible) : actions;

  const getActionColor = (type: string) => {
    switch (type) {
      case 'EMERGENCY_HALT':
        return 'text-[var(--bad)]';
      case 'PAUSE':
      case 'FLATTEN':
        return 'text-[var(--warn)]';
      case 'RESUME':
        return 'text-[var(--good)]';
      case 'OVERRIDE':
      case 'PARAMETER_CHANGE':
        return 'text-[var(--accent)]';
      default:
        return 'text-[var(--text-1)]';
    }
  };

  const getActionIcon = (type: string) => {
    switch (type) {
      case 'PAUSE': return '⏸';
      case 'RESUME': return '▶';
      case 'FLATTEN': return '📊';
      case 'OVERRIDE': return '🔧';
      case 'EMERGENCY_HALT': return '🛑';
      case 'PARAMETER_CHANGE': return '⚙️';
      case 'ANNOTATION': return '📝';
      default: return '•';
    }
  };

  return (
    <Card className={className}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-[var(--text-0)] uppercase tracking-wide">
          Manual Actions
        </h3>
        <span className="text-xs text-[var(--text-2)]">
          {actions.length} action{actions.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="space-y-2">
        {visibleActions.length === 0 ? (
          <div className="text-center py-4 text-sm text-[var(--text-2)]">
            No manual actions yet
          </div>
        ) : (
          visibleActions.map((action) => (
            <div
              key={action.id}
              className="p-3 rounded border border-[var(--stroke-0)] bg-[var(--bg-2)] hover:bg-[var(--bg-3)] transition-colors"
            >
              <div className="flex items-start gap-3">
                {/* Icon */}
                <span className="text-lg flex-shrink-0">{getActionIcon(action.type)}</span>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between mb-1">
                    <span className={`text-sm font-medium ${getActionColor(action.type)}`}>
                      {action.type.replace(/_/g, ' ')}
                    </span>
                    <Timestamp value={action.timestamp} format="time" />
                  </div>

                  <div className="text-xs text-[var(--text-2)] mb-2">
                    By: <span className="text-[var(--text-0)] font-mono">{action.operator}</span>
                  </div>

                  <div className="text-sm text-[var(--text-0)] mb-2">
                    {action.reason}
                  </div>

                  {/* Details */}
                  {action.details && Object.keys(action.details).length > 0 && (
                    <div className="text-xs font-mono text-[var(--text-1)] bg-[var(--bg-3)] p-2 rounded">
                      {Object.entries(action.details).map(([key, value]) => (
                        <div key={key}>
                          <span className="text-[var(--text-2)]">{key}:</span> {JSON.stringify(value)}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Impacted Decisions */}
                  {action.impactedDecisions && action.impactedDecisions.length > 0 && (
                    <div className="mt-2 flex items-center gap-2 flex-wrap">
                      <span className="text-xs text-[var(--text-2)]">Impacted:</span>
                      {action.impactedDecisions.map((decisionId, i) => (
                        <span
                          key={i}
                          className="text-xs font-mono text-[var(--accent)] bg-[var(--accent-bg)] px-1 rounded"
                        >
                          {decisionId}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {actions.length > visibleActions.length && (
        <div className="mt-3 text-center text-xs text-[var(--text-2)]">
          +{actions.length - visibleActions.length} more actions
        </div>
      )}
    </Card>
  );
}