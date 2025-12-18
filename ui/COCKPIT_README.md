# Trading Bot Cockpit - Live System

## Overview

This is a **production-ready demonstration** of the Live Cockpit screen for a transparent trading bot system. It embodies the philosophy of **epistemic transparency** - every decision must explain itself, every skip must show why, and nothing happens silently.

## What Was Built

### ✅ Complete Design System
- **Color tokens**: Dark graphite theme with semantic colors (good/warn/bad/info/accent)
- **Typography**: Professional sans-serif with tabular numerics
- **Spacing & Radius**: Consistent 8px-based spacing scale
- **Heatmap ramps**: 5-step intensity scales for data visualization
- **Shadows**: Minimal elevation system

### ✅ Primitive Component Library
- **StatusChip**: Gate evaluation status (PASS/FAIL/NA/ERROR)
- **Badge**: Mode, session, severity indicators
- **ReasonCodeChip**: Hoverable reason codes with descriptions
- **Card**: Container variants (default/outlined/alert)
- **DataTable**: Structured data display
- **Timestamp**: Consistent time formatting (full/time/relative)
- **NumericValue**: Formatted numbers (decimal/percentage/currency/delta)

### ✅ Domain-Specific Components
- **EventRow**: Timeline event with expandable details
- **DecisionCard**: Shows TRADE/SKIP/HALT with full EUC breakdown
- **EUCStackBar**: Edge/Uncertainty/Cost visualization with threshold markers
- **GateResultRow**: Individual gate evaluation with status
- **WhyNotCard**: Explains skip decisions with blocking gates
- **SignalTile**: Compact signal display with reliability/freshness
- **KillSwitchBanner**: Critical alert banner (cannot be dismissed)
- **ConnectionStatus**: Data connection health indicator

### ✅ Live Cockpit Screen

**Layout:**
- **Top App Bar**: System mode, session, market strip, connection status
- **Event Timeline** (left 5 columns): Real-time event stream with expandable details
- **Decision Frame** (right 7 columns): Current decision with full explanation
- **Why Not Panel**: Shows blocking gates when trades are skipped
- **Live Gate Evaluations**: All gates with required vs actual values

**State Variations:**
- ✅ SKIP decision (gates failed)
- ✅ TRADE decision (all gates pass)
- ✅ HALT decision (system pause)
- ✅ Kill Switch triggered
- ✅ Connection states (Live/Degraded/Disconnected/Catch-up)
- ✅ Bot modes (Observe/Paper/Live)

## Philosophy in Action

### Every Decision Explains Itself

**TRADE Decision shows:**
- EUC breakdown (Edge - Uncertainty - Cost)
- Capital tier and allocation
- Risk budget consumption
- Expected outcome (probability, expected value, time horizon)
- Template used (K1-K4)
- Reason codes for why this trade was taken

**SKIP Decision shows:**
- Same EUC breakdown (showing why it didn't meet threshold)
- Blocking gates with required vs actual values
- "What would need to change" for this to become a trade
- Reason codes explaining the skip

**HALT Decision shows:**
- Why the system stopped (uncertainty spike, data quality, operator pause)
- Risk state (capital tier reset, no allocation)
- Reason codes

### Gate Evaluation Transparency

Every gate shows:
- Name
- Status (PASS/FAIL/NA/ERROR)
- Required threshold
- Actual value
- Reason code (hoverable for description)

### Event Stream

Every event logged with:
- Timestamp
- Event type (DECISION/SIGNAL_UPDATE/GATE_EVAL/EXECUTION/LEARNING/HEALTH)
- Severity (INFO/WARNING/CRITICAL)
- Summary
- Expandable details with:
  - Reason codes
  - Input snapshot
  - Output snapshot

## Demo Controls

The app includes a control panel (bottom-right) to demonstrate all states:

- **Decision Type**: Switch between SKIP/TRADE/HALT
- **Connection Status**: Simulate Live/Degraded/Disconnected/Catch-up
- **Bot Mode**: Change between Observe/Paper/Live
- **Kill Switch**: Trigger and reset emergency halt

## Key Design Decisions

### 1. Skips Are First-Class Citizens
Skip decisions get the same visual weight and explanation depth as trades. This prevents the "only show wins" bias.

### 2. Expected vs Realized Always Visible
- EUC includes previous value to show delta
- Expected outcome shown before trade executes
- Sets up clean attribution later

### 3. No Silent State Changes
- Connection degradation → visible banner
- Kill switch → full-screen alert, cannot dismiss
- Every gate evaluation → logged event
- Every signal update → logged event

### 4. Reason Codes Everywhere
Every number, every decision, every state has a reason code that explains it.

### 5. Progressive Disclosure
- Event rows start collapsed
- Click to expand for full details (inputs/outputs/reason codes)
- Prevents information overload while maintaining access

## File Structure

```
/src
  /app
    /components
      /primitives      # Reusable UI primitives
      /domain          # Domain-specific components
      LiveCockpit.tsx  # Main cockpit screen
    /data
      mockData.ts      # Comprehensive mock data
    App.tsx            # Main app with demo controls
  /styles
    theme.css          # Complete design system
```

## What This Proves

### ✅ Epistemic Transparency Can Work at Speed
- All states render in real-time
- No performance issues with full explanation
- Progressive disclosure keeps it clean

### ✅ Complexity Can Be Tamed
- 8 gates evaluated simultaneously
- Multiple decision types with different requirements
- Full event stream
- All explained clearly

### ✅ The System Can Explain Itself
- Why it traded
- Why it skipped
- Why it halted
- What would need to change
- What it believes
- What it learned

## Next Steps (Phase 2)

After validating this single screen, extract into component library:
1. Document all component contracts
2. Create Storybook entries for each variant
3. Lock the interaction patterns
4. Hand off to engineering with zero ambiguity

Then build remaining screens using the same components:
- Signals Board
- Beliefs & Constraints
- Execution Quality
- Trades & Attribution
- Learning Console
- Replay Lab
- Parameter Studio
- System Health

## Critical Success Metrics

This screen succeeds if an operator can answer at any moment:

1. ✅ **What did the bot just decide?** → DecisionCard
2. ✅ **Why did it decide that?** → EUC + Reason Codes
3. ✅ **Why didn't it trade?** → WhyNotCard + Blocking Gates
4. ✅ **What's the system state?** → Top bar + Connection status
5. ✅ **What just happened?** → Event timeline
6. ✅ **Can I trust the data?** → Connection status + Kill switch
7. ✅ **What would make this a trade?** → "What would change" section
8. ✅ **Is anything going wrong?** → Event severity + Gate failures

**All answered. Zero guesswork.**

---

This is not a dashboard. This is a **machine that explains itself faster than it acts**.
