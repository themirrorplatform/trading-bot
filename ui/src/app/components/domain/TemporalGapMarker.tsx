/**
 * TemporalGapMarker - Shows when there's a gap in the event timeline
 * Critical for temporal honesty - no implied continuity where none exists
 */

interface TemporalGapMarkerProps {
  gapDuration: number; // seconds
  reason?: string;
  className?: string;
}

export function TemporalGapMarker({ gapDuration, reason, className = '' }: TemporalGapMarkerProps) {
  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  };

  return (
    <div className={`flex items-center justify-center py-2 px-4 bg-[var(--bg-2)] border-y border-dashed border-[var(--stroke-0)] ${className}`}>
      <div className="text-center">
        <div className="text-xs text-[var(--text-2)] uppercase tracking-wide mb-1">
          No Events
        </div>
        <div className="text-sm font-mono text-[var(--text-1)]">
          {formatDuration(gapDuration)}
        </div>
        {reason && (
          <div className="text-xs text-[var(--text-2)] mt-1">
            {reason}
          </div>
        )}
      </div>
    </div>
  );
}
