/**
 * DriftAlertBanner - Warns about model drift, overconfidence, saturation, runaway
 * Critical for detecting when the bot is degrading
 */

import { Card } from '../primitives/Card';
import { Timestamp } from '../primitives/Timestamp';

interface DriftAlert {
  type: 'BELIEF_DRIFT' | 'OVERCONFIDENCE' | 'GATE_SATURATION' | 'LEARNING_RUNAWAY';
  severity: 'WARNING' | 'CRITICAL';
  message: string;
  details: string;
  detectedAt: string;
  affectedComponents: string[];
  recommendedAction?: string;
}

interface DriftAlertBannerProps {
  alerts: DriftAlert[];
  onDismiss?: (index: number) => void;
  className?: string;
}

export function DriftAlertBanner({ alerts, onDismiss, className = '' }: DriftAlertBannerProps) {
  if (alerts.length === 0) return null;

  const getAlertStyles = (type: string) => {
    const styles = {
      BELIEF_DRIFT: {
        icon: '📊',
        bg: 'bg-[var(--warn-bg)]',
        border: 'border-[var(--stroke-warn)]',
        text: 'text-[var(--warn)]'
      },
      OVERCONFIDENCE: {
        icon: '⚠️',
        bg: 'bg-[var(--bad-bg)]',
        border: 'border-[var(--stroke-error)]',
        text: 'text-[var(--bad)]'
      },
      GATE_SATURATION: {
        icon: '🚧',
        bg: 'bg-[var(--warn-bg)]',
        border: 'border-[var(--stroke-warn)]',
        text: 'text-[var(--warn)]'
      },
      LEARNING_RUNAWAY: {
        icon: '🔥',
        bg: 'bg-[var(--bad-bg)]',
        border: 'border-[var(--stroke-error)]',
        text: 'text-[var(--bad)]'
      }
    };
    return styles[type as keyof typeof styles];
  };

  return (
    <div className={`space-y-2 ${className}`}>
      {alerts.map((alert, index) => {
        const styles = getAlertStyles(alert.type);
        
        return (
          <Card
            key={index}
            variant="alert"
            alertType={alert.severity === 'CRITICAL' ? 'error' : 'warning'}
            className="relative"
          >
            <div className="flex items-start gap-3">
              {/* Icon */}
              <span className="text-2xl flex-shrink-0">{styles.icon}</span>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h4 className={`font-semibold ${styles.text} mb-1`}>
                      {alert.type.replace(/_/g, ' ')}
                    </h4>
                    <p className="text-sm text-[var(--text-0)]">
                      {alert.message}
                    </p>
                  </div>
                  <Timestamp value={alert.detectedAt} format="time" />
                </div>

                {/* Details */}
                <div className="text-xs text-[var(--text-1)] mb-2">
                  {alert.details}
                </div>

                {/* Affected Components */}
                {alert.affectedComponents.length > 0 && (
                  <div className="mb-2">
                    <span className="text-xs text-[var(--text-2)] uppercase tracking-wide mr-2">
                      Affected:
                    </span>
                    {alert.affectedComponents.map((comp, i) => (
                      <span
                        key={i}
                        className="inline-block mr-2 text-xs font-mono text-[var(--accent)]"
                      >
                        {comp}
                      </span>
                    ))}
                  </div>
                )}

                {/* Recommended Action */}
                {alert.recommendedAction && (
                  <div className={`text-xs font-medium ${styles.text}`}>
                    → {alert.recommendedAction}
                  </div>
                )}
              </div>

              {/* Dismiss (if allowed) */}
              {onDismiss && (
                <button
                  onClick={() => onDismiss(index)}
                  className="flex-shrink-0 text-[var(--text-2)] hover:text-[var(--text-0)] transition-colors"
                  title="Acknowledge"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
          </Card>
        );
      })}
    </div>
  );
}
