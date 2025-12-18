import React, { useState } from 'react';
import { cn } from './ui/utils';
import { SeverityDot } from './SeverityDot';
import { ChevronDown } from 'lucide-react';
import type { Event } from '../types/trading-types';

interface EventRowProps {
  event: Event;
  onExpand?: (event: Event) => void;
}

export function EventRow({ event, onExpand }: EventRowProps) {
  const [expanded, setExpanded] = useState(false);

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3
    });
  };

  const handleClick = () => {
    setExpanded(!expanded);
    if (onExpand && !expanded) {
      onExpand(event);
    }
  };

  return (
    <div
      className={cn(
        'border-b border-[#22304A] hover:bg-[#111826] transition-colors cursor-pointer',
        expanded && 'bg-[#111826]'
      )}
      onClick={handleClick}
    >
      <div className="flex items-center gap-3 px-4 py-3">
        <SeverityDot severity={event.severity} />
        
        <span className="text-xs text-[#7F93B2] font-mono tabular-nums w-24">
          {formatTime(event.timestamp)}
        </span>

        <span className="text-xs font-mono text-[#B38BFF] w-40">
          {event.event_type}
        </span>

        <span className="text-sm text-[#E7EEF9] flex-1">
          {event.summary}
        </span>

        <ChevronDown
          className={cn(
            'w-4 h-4 text-[#7F93B2] transition-transform',
            expanded && 'rotate-180'
          )}
        />
      </div>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-[#22304A] bg-[#162033]">
          {event.reason_codes.length > 0 && (
            <div className="pt-3">
              <div className="text-xs text-[#7F93B2] mb-2">Reason Codes</div>
              <div className="flex flex-wrap gap-2">
                {event.reason_codes.map((code, i) => (
                  <span
                    key={i}
                    className="px-2 py-1 bg-[#111826] border border-[#22304A] rounded text-xs font-mono text-[#B8C7E0]"
                  >
                    {code}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div>
            <div className="text-xs text-[#7F93B2] mb-2">Payload</div>
            <pre className="text-xs font-mono text-[#B8C7E0] bg-[#111826] p-3 rounded overflow-x-auto">
              {JSON.stringify(event.payload, null, 2)}
            </pre>
          </div>

          <div className="flex gap-2">
            <button className="px-3 py-1.5 bg-[#B38BFF] text-[#0B0F14] rounded text-xs hover:bg-[#9B6FFF] transition-colors">
              Jump to Replay
            </button>
            <button className="px-3 py-1.5 bg-[#162033] text-[#B8C7E0] border border-[#22304A] rounded text-xs hover:border-[#B38BFF] transition-colors">
              Compare Against Previous
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
