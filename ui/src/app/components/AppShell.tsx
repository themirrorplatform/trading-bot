import React, { useState } from 'react';
import { cn } from './ui/utils';
import { StatusBadge } from './StatusBadge';
import type { BotMode, KillSwitchState, Session, MarketData, SystemHealth } from '../types/trading-types';
import { 
  Activity, 
  Radio, 
  Brain, 
  Zap, 
  TrendingUp, 
  GraduationCap, 
  RotateCcw, 
  Settings, 
  Heart,
  ShieldAlert
} from 'lucide-react';

interface AppShellProps {
  children: React.ReactNode;
  activePage: string;
  onPageChange: (page: string) => void;
  marketData: MarketData;
  systemHealth: SystemHealth;
  botMode: BotMode;
  killSwitch: KillSwitchState;
}

const navItems = [
  { id: 'cockpit', label: 'Live Cockpit', icon: Activity },
  { id: 'signals', label: 'Signals', icon: Radio },
  { id: 'beliefs', label: 'Beliefs', icon: Brain },
  { id: 'execution', label: 'Execution', icon: Zap },
  { id: 'trades', label: 'Trades', icon: TrendingUp },
  { id: 'learning', label: 'Learning', icon: GraduationCap },
  { id: 'replay', label: 'Replay Lab', icon: RotateCcw },
  { id: 'parameters', label: 'Parameters', icon: Settings },
  { id: 'health', label: 'System', icon: Heart },
];

export function AppShell({
  children,
  activePage,
  onPageChange,
  marketData,
  systemHealth,
  botMode,
  killSwitch,
}: AppShellProps) {
  const [railExpanded, setRailExpanded] = useState(false);

  const getBotModeStatus = (mode: BotMode) => {
    if (mode === 'LIVE') return 'bad';
    if (mode === 'PAPER') return 'warn';
    return 'info';
  };

  return (
    <div className="h-screen flex flex-col bg-[#0B0F14] text-[#E7EEF9]">
      {/* Top App Bar */}
      <div className="h-14 border-b border-[#22304A] bg-[#111826] flex items-center justify-between px-6">
        <div className="flex items-center gap-4">
          <h1 className="font-semibold text-[#E7EEF9]">Bot Cockpit</h1>
          <StatusBadge status={getBotModeStatus(botMode)}>
            {botMode}
          </StatusBadge>
        </div>

        <div className="flex items-center gap-6">
          {/* Market Info */}
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-[#7F93B2]">{marketData.symbol}</span>
              <StatusBadge status="neutral">
                {marketData.session}
              </StatusBadge>
            </div>
            <div className="text-[#E7EEF9] font-mono tabular-nums">
              {marketData.last_price.toFixed(2)}
            </div>
            <div
              className={cn(
                'font-mono tabular-nums',
                marketData.change >= 0 ? 'text-[#2ED47A]' : 'text-[#FF5A5F]'
              )}
            >
              {marketData.change >= 0 ? '+' : ''}{marketData.change.toFixed(2)} ({marketData.change_pct >= 0 ? '+' : ''}{marketData.change_pct.toFixed(2)}%)
            </div>
          </div>

          {/* Kill Switch */}
          {killSwitch === 'TRIPPED' ? (
            <StatusBadge status="bad" className="gap-2">
              <ShieldAlert className="w-3.5 h-3.5" />
              KILL SWITCH TRIPPED
            </StatusBadge>
          ) : (
            <StatusBadge status="good" className="gap-2">
              <ShieldAlert className="w-3.5 h-3.5" />
              ARMED
            </StatusBadge>
          )}

          {/* Data Health */}
          <div className="flex items-center gap-2">
            <div className={cn(
              'w-2 h-2 rounded-full',
              systemHealth.websocket_connected ? 'bg-[#2ED47A]' : 'bg-[#FF5A5F]'
            )} />
            <span className="text-xs text-[#7F93B2]">
              {systemHealth.latency_ms}ms
            </span>
          </div>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Left Rail */}
        <div
          className={cn(
            'border-r border-[#22304A] bg-[#0B0F14] transition-all duration-200 flex flex-col',
            railExpanded ? 'w-60' : 'w-18'
          )}
          onMouseEnter={() => setRailExpanded(true)}
          onMouseLeave={() => setRailExpanded(false)}
        >
          <nav className="flex-1 py-4">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activePage === item.id;
              
              return (
                <button
                  key={item.id}
                  onClick={() => onPageChange(item.id)}
                  className={cn(
                    'w-full flex items-center gap-3 px-6 py-3 transition-colors',
                    isActive
                      ? 'bg-[#162033] text-[#B38BFF] border-r-2 border-[#B38BFF]'
                      : 'text-[#B8C7E0] hover:bg-[#111826] hover:text-[#E7EEF9]'
                  )}
                >
                  <Icon className="w-5 h-5 flex-shrink-0" />
                  <span
                    className={cn(
                      'text-sm whitespace-nowrap transition-opacity',
                      railExpanded ? 'opacity-100' : 'opacity-0'
                    )}
                  >
                    {item.label}
                  </span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Main Content */}
        <div className="flex-1 overflow-auto">
          {children}
        </div>
      </div>
    </div>
  );
}
