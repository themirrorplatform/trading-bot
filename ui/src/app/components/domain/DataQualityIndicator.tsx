/**
 * DataQualityIndicator - Shows data feed health, latency, missing bars
 * Critical for knowing when the bot is seeing degraded data
 */

import { Card } from '../primitives/Card';
import { NumericValue } from '../primitives/NumericValue';

interface DataQuality {
  feedName: string;
  status: 'HEALTHY' | 'DEGRADED' | 'FAILING';
  latency: {
    current: number;
    baseline: number;
    threshold: number;
  };
  missingBars: {
    count: number;
    lastMissing: string;
  };
  dataFreshness: number; // seconds since last update
  errorRate: number; // 0-1
}

interface DataQualityIndicatorProps {
  feeds: DataQuality[];
  className?: string;
}

export function DataQualityIndicator({ feeds, className = '' }: DataQualityIndicatorProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'HEALTHY': return 'text-[var(--good)]';
      case 'DEGRADED': return 'text-[var(--warn)]';
      case 'FAILING': return 'text-[var(--bad)]';
      default: return 'text-[var(--text-2)]';
    }
  };

  const getStatusBg = (status: string) => {
    switch (status) {
      case 'HEALTHY': return 'bg-[var(--good)]';
      case 'DEGRADED': return 'bg-[var(--warn)]';
      case 'FAILING': return 'bg-[var(--bad)]';
      default: return 'bg-[var(--neutral)]';
    }
  };

  return (
    <Card className={className}>
      <h3 className="text-sm font-semibold text-[var(--text-0)] uppercase tracking-wide mb-4">
        Data Quality
      </h3>

      <div className="space-y-3">
        {feeds.map((feed, index) => (
          <div
            key={index}
            className="p-3 rounded border border-[var(--stroke-0)] bg-[var(--bg-2)]"
          >
            {/* Feed Header */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${getStatusBg(feed.status)}`} />
                <span className="text-sm font-medium text-[var(--text-0)]">
                  {feed.feedName}
                </span>
              </div>
              <span className={`text-xs font-medium uppercase ${getStatusColor(feed.status)}`}>
                {feed.status}
              </span>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 gap-3">
              {/* Latency */}
              <div>
                <div className="text-xs text-[var(--text-2)] mb-1">Latency</div>
                <div className="font-mono text-sm">
                  <span className={
                    feed.latency.current > feed.latency.threshold
                      ? 'text-[var(--bad)]'
                      : feed.latency.current > feed.latency.baseline * 1.5
                      ? 'text-[var(--warn)]'
                      : 'text-[var(--good)]'
                  }>
                    {feed.latency.current}ms
                  </span>
                  <span className="text-[var(--text-2)] ml-1">
                    / {feed.latency.threshold}ms
                  </span>
                </div>
              </div>

              {/* Freshness */}
              <div>
                <div className="text-xs text-[var(--text-2)] mb-1">Freshness</div>
                <div className="font-mono text-sm">
                  <span className={
                    feed.dataFreshness > 5
                      ? 'text-[var(--bad)]'
                      : feed.dataFreshness > 2
                      ? 'text-[var(--warn)]'
                      : 'text-[var(--good)]'
                  }>
                    {feed.dataFreshness}s
                  </span>
                </div>
              </div>

              {/* Missing Bars */}
              <div>
                <div className="text-xs text-[var(--text-2)] mb-1">Missing Bars</div>
                <div className="font-mono text-sm">
                  <span className={
                    feed.missingBars.count > 0 ? 'text-[var(--warn)]' : 'text-[var(--good)]'
                  }>
                    {feed.missingBars.count}
                  </span>
                </div>
              </div>

              {/* Error Rate */}
              <div>
                <div className="text-xs text-[var(--text-2)] mb-1">Error Rate</div>
                <div className="font-mono text-sm">
                  <span className={
                    feed.errorRate > 0.05
                      ? 'text-[var(--bad)]'
                      : feed.errorRate > 0.01
                      ? 'text-[var(--warn)]'
                      : 'text-[var(--good)]'
                  }>
                    <NumericValue value={feed.errorRate} format="percentage" decimals={2} />
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
