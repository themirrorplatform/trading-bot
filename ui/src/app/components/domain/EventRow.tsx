/**
 * EventRow - Individual event in the timeline
 * Displays timestamp, type, severity, and summary with expand capability
 * Now supports: DECISION, SIGNAL_UPDATE, GATE_EVAL, EXECUTION, LEARNING, HEALTH,
 *               BAR_CLOSE, ORDER_SUBMIT, FILL, EXIT, ATTRIBUTION, CONSTRAINT
 */

import { Timestamp } from '../primitives/Timestamp';
import { Badge } from '../primitives/Badge';
import { useState } from 'react';

interface EventRowProps {
  event: {
    id: string;
    timestamp: string;
    type: 'DECISION' | 'SIGNAL_UPDATE' | 'GATE_EVAL' | 'EXECUTION' | 'LEARNING' | 'HEALTH' | 
          'BAR_CLOSE' | 'ORDER_SUBMIT' | 'FILL' | 'EXIT' | 'ATTRIBUTION' | 'CONSTRAINT';
    severity: 'INFO' | 'WARNING' | 'CRITICAL';
    summary: string;
    details?: {
      reasonCodes?: string[];
      inputs?: Record<string, any>;
      outputs?: Record<string, any>;
    };
  };
  onExpand?: (eventId: string) => void;
}

export function EventRow({ event, onExpand }: EventRowProps) {
  const [expanded, setExpanded] = useState(false);

  const severityDot = {
    INFO: 'bg-[var(--info)]',
    WARNING: 'bg-[var(--warn)]',
    CRITICAL: 'bg-[var(--bad)]'
  };

  const handleClick = () => {
    setExpanded(!expanded);
    if (onExpand) onExpand(event.id);
  };

  return (
    <div className="border-b border-[var(--stroke-1)] last:border-0">
      <div
        className="flex items-start gap-3 p-3 hover:bg-[var(--bg-2)] cursor-pointer transition-colors"
        onClick={handleClick}
      >
        {/* Severity indicator */}
        <div className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${severityDot[event.severity]}`} />

        {/* Timestamp */}
        <div className="flex-shrink-0 w-24">
          <Timestamp value={event.timestamp} format="time" />
        </div>

        {/* Event type */}
        <div className="flex-shrink-0">
          <span className="text-[0.75rem] font-mono text-[var(--text-1)] uppercase">
            {event.type}
          </span>
        </div>

        {/* Summary */}
        <div className="flex-1 text-[0.875rem] text-[var(--text-0)]">
          {event.summary}
        </div>

        {/* Expand indicator */}
        <div className="flex-shrink-0 text-[var(--text-2)]">
          <svg
            className={`w-4 h-4 transition-transform ${expanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {/* Expanded details */}
      {expanded && event.details && (
        <div className="px-3 pb-3 ml-11 space-y-2 text-[0.75rem]">
          {event.details.reasonCodes && event.details.reasonCodes.length > 0 && (
            <div>
              <span className="text-[var(--text-2)] uppercase tracking-wide mr-2">Reason Codes:</span>
              {event.details.reasonCodes.map((code, i) => (
                <span key={i} className="inline-block mr-2 font-mono text-[var(--accent)]">
                  {code}
                </span>
              ))}
            </div>
          )}
          {event.details.inputs && (
            <div>
              <span className="text-[var(--text-2)] uppercase tracking-wide block mb-1">Inputs:</span>
              <pre className="text-[0.6875rem] font-mono text-[var(--text-1)] bg-[var(--bg-3)] p-2 rounded overflow-x-auto">
                {JSON.stringify(event.details.inputs, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}