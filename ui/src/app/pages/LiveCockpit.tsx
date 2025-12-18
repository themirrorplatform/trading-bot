import React, { useState } from 'react';
import { EventRow } from '../components/EventRow';
import { DecisionCard } from '../components/DecisionCard';
import { GateTrace } from '../components/GateTrace';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ScrollArea } from '../components/ui/scroll-area';
import type { Event, DecisionRecord } from '../types/trading-types';

interface LiveCockpitProps {
  events: Event[];
  currentDecision: DecisionRecord | null;
}

export function LiveCockpit({ events, currentDecision }: LiveCockpitProps) {
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);

  return (
    <div className="h-full p-6 grid grid-cols-12 gap-6">
      {/* Event Feed - 8 columns */}
      <div className="col-span-8 space-y-4">
        <h2 className="font-semibold text-[#E7EEF9]">Now Timeline</h2>
        <div className="bg-[#111826] border border-[#22304A] rounded-xl overflow-hidden">
          <ScrollArea className="h-[calc(100vh-200px)]">
            {events.length === 0 ? (
              <div className="text-center text-[#7F93B2] py-12">
                No events yet — waiting for first bar close
              </div>
            ) : (
              events.map((event) => (
                <EventRow
                  key={event.event_id}
                  event={event}
                  onExpand={setSelectedEvent}
                />
              ))
            )}
          </ScrollArea>
        </div>
      </div>

      {/* Decision Frame - 4 columns */}
      <div className="col-span-4 space-y-4">
        <h2 className="font-semibold text-[#E7EEF9]">Decision Frame</h2>
        <DecisionCard decision={currentDecision} />

        {/* Why Not / Gate Trace Tabs */}
        {currentDecision && (
          <div className="bg-[#111826] border border-[#22304A] rounded-xl overflow-hidden">
            <Tabs defaultValue="gates" className="w-full">
              <TabsList className="w-full grid grid-cols-2 bg-[#162033] border-b border-[#22304A] rounded-none">
                <TabsTrigger value="gates">Gate Trace</TabsTrigger>
                <TabsTrigger value="whynot">Why Not?</TabsTrigger>
              </TabsList>
              
              <TabsContent value="gates" className="p-4">
                <ScrollArea className="h-[400px]">
                  <GateTrace gates={currentDecision.gates} />
                </ScrollArea>
              </TabsContent>
              
              <TabsContent value="whynot" className="p-4">
                {currentDecision.why_not ? (
                  <div className="space-y-4">
                    <div>
                      <div className="text-xs text-[#7F93B2] mb-2">Primary Blocker</div>
                      <div className="text-sm text-[#E7EEF9] p-3 bg-[#162033] rounded">
                        {currentDecision.why_not.primary_blocker}
                      </div>
                    </div>

                    <div>
                      <div className="text-xs text-[#7F93B2] mb-2">Failed Gate</div>
                      <div className="p-3 bg-[#162033] rounded space-y-2">
                        <div className="text-sm text-[#E7EEF9]">
                          {currentDecision.why_not.failed_gate.gate_name}
                        </div>
                        <div className="flex items-center justify-between text-xs font-mono tabular-nums">
                          <span className="text-[#7F93B2]">
                            Required ≤ {currentDecision.why_not.failed_gate.threshold_required?.toFixed(2)}
                          </span>
                          <span className="text-[#FF5A5F]">
                            Current: {currentDecision.why_not.failed_gate.current_value?.toFixed(2)}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div>
                      <div className="text-xs text-[#7F93B2] mb-2">What Would Need to Change</div>
                      <div className="text-sm text-[#B8C7E0] p-3 bg-[#162033] rounded">
                        {currentDecision.why_not.what_would_change}
                      </div>
                    </div>

                    {currentDecision.why_not.supporting_evidence.length > 0 && (
                      <div>
                        <div className="text-xs text-[#7F93B2] mb-2">Supporting Evidence</div>
                        <div className="space-y-1">
                          {currentDecision.why_not.supporting_evidence.map((ev, i) => (
                            <div key={i} className="text-xs text-[#B8C7E0] p-2 bg-[#162033] rounded">
                              • {ev}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center text-[#7F93B2] py-8">
                    No gate failures — decision was to trade or no blocking occurred
                  </div>
                )}
              </TabsContent>
            </Tabs>
          </div>
        )}
      </div>
    </div>
  );
}
