import React, { useState } from 'react';
import { cn } from '../components/ui/utils';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { ScrollArea } from '../components/ui/scroll-area';
import { CheckCircle2, XCircle, FileCode, AlertCircle } from 'lucide-react';
import type { ConfigPatch } from '../types/trading-types';

interface ParameterStudioProps {
  patches: ConfigPatch[];
}

export function ParameterStudio({ patches }: ParameterStudioProps) {
  const [selectedSection, setSelectedSection] = useState('constitution');
  const [patchName, setPatchName] = useState('');
  const [patchDescription, setPatchDescription] = useState('');
  const [safetyChecks, setSafetyChecks] = useState({
    replay_tests_complete: false,
    invariants_passed: false,
    decision_delta_generated: false,
  });

  const configSections = [
    { id: 'constitution', label: 'Constitution / Invariants', icon: FileCode },
    { id: 'risk', label: 'Risk Limits', icon: FileCode },
    { id: 'execution', label: 'Execution', icon: FileCode },
    { id: 'templates', label: 'Strategy Templates', icon: FileCode },
    { id: 'signals', label: 'Signal Reliabilities', icon: FileCode },
    { id: 'constraints', label: 'Constraint Matrix', icon: FileCode },
    { id: 'gates', label: 'Gates', icon: FileCode },
  ];

  const canApplyPatch = Object.values(safetyChecks).every(Boolean) && patchName && patchDescription;

  return (
    <div className="h-full p-6 grid grid-cols-12 gap-6">
      {/* Left: Config Tree */}
      <div className="col-span-3 space-y-4">
        <div>
          <h2 className="font-semibold text-[#E7EEF9] mb-1">Configuration</h2>
          <p className="text-sm text-[#7F93B2]">Current loaded config</p>
        </div>

        <ScrollArea className="h-[calc(100vh-200px)]">
          <div className="space-y-2">
            {configSections.map((section) => {
              const Icon = section.icon;
              const isSelected = selectedSection === section.id;

              return (
                <button
                  key={section.id}
                  onClick={() => setSelectedSection(section.id)}
                  className={cn(
                    'w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all text-left',
                    isSelected
                      ? 'bg-[#162033] border border-[#B38BFF] text-[#E7EEF9]'
                      : 'bg-[#111826] border border-[#22304A] text-[#B8C7E0] hover:border-[#B38BFF]'
                  )}
                >
                  <Icon className="w-4 h-4" />
                  <span className="text-sm">{section.label}</span>
                </button>
              );
            })}
          </div>
        </ScrollArea>
      </div>

      {/* Center: Config Editor */}
      <div className="col-span-5 space-y-4">
        <div>
          <h2 className="font-semibold text-[#E7EEF9] mb-1">Edit Configuration</h2>
          <p className="text-sm text-[#7F93B2]">{configSections.find(s => s.id === selectedSection)?.label}</p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {/* Before */}
          <div className="bg-[#111826] border border-[#22304A] rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-[#22304A] bg-[#162033]">
              <div className="text-xs font-medium text-[#E7EEF9]">Current (Before)</div>
            </div>
            <ScrollArea className="h-[600px]">
              <pre className="text-xs font-mono text-[#B8C7E0] p-4">
{`# Constitution: Invariants
max_positions: 1
max_daily_loss: 1000
max_single_trade_risk: 200

# Gates
friction_threshold: 4.75
uncertainty_threshold: 5.0
euc_min: 0.0

# Strategy Templates
K1:
  entry_type: "LIMIT"
  stop_distance: 10
  target_multiplier: 2.0
  
K2:
  entry_type: "MARKET"
  stop_distance: 8
  target_multiplier: 1.5`}
              </pre>
            </ScrollArea>
          </div>

          {/* After (Proposed Changes) */}
          <div className="bg-[#111826] border border-[#B38BFF] rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-[#B38BFF] bg-[#6B509F]/20">
              <div className="text-xs font-medium text-[#E7EEF9]">Proposed (After)</div>
            </div>
            <ScrollArea className="h-[600px]">
              <pre className="text-xs font-mono text-[#B8C7E0] p-4">
{`# Constitution: Invariants
max_positions: 1
max_daily_loss: 1000
max_single_trade_risk: 200

# Gates
`}
                <span className="bg-[#1A7A45]/30 text-[#2ED47A]">friction_threshold: 4.50  # Changed from 4.75</span>
{`
uncertainty_threshold: 5.0
euc_min: 0.0

# Strategy Templates
K1:
  entry_type: "LIMIT"
  stop_distance: 10
  target_multiplier: 2.0
  
K2:
  entry_type: "MARKET"
  stop_distance: 8
  target_multiplier: 1.5`}
              </pre>
            </ScrollArea>
          </div>
        </div>

        {/* Diff Summary */}
        <div className="bg-[#111826] border border-[#22304A] rounded-xl p-4">
          <div className="text-xs font-medium text-[#E7EEF9] mb-3">Changes Summary</div>
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm">
              <div className="w-2 h-2 rounded-full bg-[#2ED47A]"></div>
              <span className="text-[#E7EEF9]">gates.friction_threshold:</span>
              <span className="text-[#7F93B2]">4.75 →</span>
              <span className="text-[#2ED47A]">4.50</span>
            </div>
          </div>
        </div>
      </div>

      {/* Right: Patch Metadata & Safety Checks */}
      <div className="col-span-4 space-y-4">
        <div>
          <h2 className="font-semibold text-[#E7EEF9] mb-1">Patch Metadata</h2>
          <p className="text-sm text-[#7F93B2]">Required before applying</p>
        </div>

        <div className="bg-[#111826] border border-[#22304A] rounded-xl p-6 space-y-4">
          {/* Patch Name */}
          <div>
            <label className="text-xs text-[#7F93B2] mb-2 block">Patch Name</label>
            <Input
              value={patchName}
              onChange={(e) => setPatchName(e.target.value)}
              placeholder="e.g., Reduce friction threshold"
              className="bg-[#162033] border-[#22304A] text-[#E7EEF9]"
            />
          </div>

          {/* Description */}
          <div>
            <label className="text-xs text-[#7F93B2] mb-2 block">Description</label>
            <Textarea
              value={patchDescription}
              onChange={(e) => setPatchDescription(e.target.value)}
              placeholder="Explain the intended behavioral impact..."
              rows={4}
              className="bg-[#162033] border-[#22304A] text-[#E7EEF9]"
            />
          </div>

          {/* Scope */}
          <div>
            <label className="text-xs text-[#7F93B2] mb-2 block">Scope</label>
            <div className="flex flex-wrap gap-2">
              <div className="px-2 py-1 bg-[#285A8F] text-[#4DA3FF] rounded text-xs">gates</div>
              <div className="px-2 py-1 bg-[#285A8F] text-[#4DA3FF] rounded text-xs">friction</div>
            </div>
          </div>

          {/* Risk Rating */}
          <div>
            <label className="text-xs text-[#7F93B2] mb-2 block">Risk Rating</label>
            <select className="w-full bg-[#162033] border border-[#22304A] rounded p-2 text-[#E7EEF9]">
              <option value="low">Low - Minor adjustment</option>
              <option value="medium" selected>Medium - Affects decision logic</option>
              <option value="high">High - Core system change</option>
            </select>
          </div>
        </div>

        {/* Safety Checks */}
        <div className="bg-[#111826] border border-[#22304A] rounded-xl p-6 space-y-4">
          <div className="text-sm font-medium text-[#E7EEF9]">Safety Checks</div>
          <p className="text-xs text-[#7F93B2]">All must pass before applying patch</p>

          <div className="space-y-3">
            {/* Replay Tests */}
            <button
              onClick={() => setSafetyChecks({ ...safetyChecks, replay_tests_complete: !safetyChecks.replay_tests_complete })}
              className={cn(
                'w-full flex items-center gap-3 p-3 rounded-lg border transition-all',
                safetyChecks.replay_tests_complete
                  ? 'bg-[#1A7A45]/10 border-[#2ED47A]/20'
                  : 'bg-[#162033] border-[#22304A] hover:border-[#B38BFF]'
              )}
            >
              {safetyChecks.replay_tests_complete ? (
                <CheckCircle2 className="w-5 h-5 text-[#2ED47A]" />
              ) : (
                <XCircle className="w-5 h-5 text-[#7F93B2]" />
              )}
              <div className="flex-1 text-left">
                <div className="text-sm text-[#E7EEF9]">Replay Tests Complete</div>
                <div className="text-xs text-[#7F93B2] mt-0.5">Run against last 100 decisions</div>
              </div>
            </button>

            {/* Invariants Check */}
            <button
              onClick={() => setSafetyChecks({ ...safetyChecks, invariants_passed: !safetyChecks.invariants_passed })}
              className={cn(
                'w-full flex items-center gap-3 p-3 rounded-lg border transition-all',
                safetyChecks.invariants_passed
                  ? 'bg-[#1A7A45]/10 border-[#2ED47A]/20'
                  : 'bg-[#162033] border-[#22304A] hover:border-[#B38BFF]'
              )}
            >
              {safetyChecks.invariants_passed ? (
                <CheckCircle2 className="w-5 h-5 text-[#2ED47A]" />
              ) : (
                <XCircle className="w-5 h-5 text-[#7F93B2]" />
              )}
              <div className="flex-1 text-left">
                <div className="text-sm text-[#E7EEF9]">Invariants Check Passed</div>
                <div className="text-xs text-[#7F93B2] mt-0.5">No constitution violations</div>
              </div>
            </button>

            {/* Decision Delta */}
            <button
              onClick={() => setSafetyChecks({ ...safetyChecks, decision_delta_generated: !safetyChecks.decision_delta_generated })}
              className={cn(
                'w-full flex items-center gap-3 p-3 rounded-lg border transition-all',
                safetyChecks.decision_delta_generated
                  ? 'bg-[#1A7A45]/10 border-[#2ED47A]/20'
                  : 'bg-[#162033] border-[#22304A] hover:border-[#B38BFF]'
              )}
            >
              {safetyChecks.decision_delta_generated ? (
                <CheckCircle2 className="w-5 h-5 text-[#2ED47A]" />
              ) : (
                <XCircle className="w-5 h-5 text-[#7F93B2]" />
              )}
              <div className="flex-1 text-left">
                <div className="text-sm text-[#E7EEF9]">Decision Delta Generated</div>
                <div className="text-xs text-[#7F93B2] mt-0.5">8.5% decisions changed, +3 trades</div>
              </div>
            </button>
          </div>
        </div>

        {/* Apply Button */}
        <button
          disabled={!canApplyPatch}
          className={cn(
            'w-full px-4 py-3 rounded-lg transition-all',
            canApplyPatch
              ? 'bg-[#B38BFF] text-[#0B0F14] hover:bg-[#9B6FFF]'
              : 'bg-[#22304A] text-[#7F93B2] cursor-not-allowed'
          )}
        >
          {canApplyPatch ? 'Apply Patch' : 'Complete Safety Checks to Apply'}
        </button>

        {canApplyPatch && (
          <div className="bg-[#8B5A00]/10 border border-[#FFB020]/20 rounded-lg p-3 text-xs text-[#FFB020]">
            <AlertCircle className="w-4 h-4 inline mr-2" />
            This will create an immutable CONFIG_PATCH_APPLIED event.
          </div>
        )}

        {/* Patch History */}
        <div className="bg-[#111826] border border-[#22304A] rounded-xl p-6">
          <div className="text-sm font-medium text-[#E7EEF9] mb-4">Recent Patches</div>
          <ScrollArea className="h-48">
            <div className="space-y-2">
              {patches.map((patch) => (
                <div key={patch.patch_id} className="p-3 bg-[#162033] rounded text-xs">
                  <div className="text-[#E7EEF9] font-medium">{patch.name}</div>
                  <div className="text-[#7F93B2] mt-1">
                    {patch.behavioral_impact.decisions_changed_pct.toFixed(1)}% decisions changed
                  </div>
                  {patch.applied_at && (
                    <div className="text-[#7F93B2] mt-1">
                      Applied: {new Date(patch.applied_at).toLocaleDateString()}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>
      </div>
    </div>
  );
}
