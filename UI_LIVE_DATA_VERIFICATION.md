# UI Components Live Data Verification Report
**Generated:** December 27, 2025

## Executive Summary
The UI build is now working and Netlify configuration has been fixed to use `VITE_DATA_SOURCE=supabase`. However, there is a **critical data structure mismatch** between what Supabase provides and what UI components expect. This will cause runtime errors when live data flows.

---

## Data Layer Status

### ✅ COMPLETED
- [x] App.tsx wired to fetch from Supabase
- [x] Real-time subscriptions configured
- [x] Data fetching queries created
- [x] Feature flag system (VITE_DATA_SOURCE) implemented
- [x] Build verified working
- [x] Netlify config set to use Supabase data source
- [x] @supabase/supabase-js dependency added
- [x] Missing files (config.ts, queries.ts, realtime.ts) committed

### ⚠️  CRITICAL ISSUE - Data Structure Mismatch

#### Supabase Events Table Schema
```typescript
events {
  id: string                  // Primary key
  stream_id: string          
  timestamp: string          
  event_type: string         
  payload: Json              
  config_hash: string        
  created_at: string         
}
```

#### UI Component Event Interface Expected
```typescript
Event {
  event_id: string           // ❌ Supabase uses 'id'
  timestamp: string          // ✅ Match
  event_type: EventType      // ✅ Match (but type is string in Supabase)
  severity: Severity         // ❌ MISSING in Supabase
  summary: string            // ❌ MISSING in Supabase
  payload: Record<string>    // ✅ Match
  reason_codes: string[]     // ❌ MISSING in Supabase
}
```

#### Impact
When App.tsx fetches events from Supabase:
1. Components receive `{id, timestamp, event_type, payload, ...}` 
2. But they expect `{event_id, timestamp, event_type, severity, summary, payload, reason_codes}`
3. Missing fields (severity, summary, reason_codes) will be undefined
4. LiveCockpit and other components will have runtime errors

---

## UI Components Audit

### 8 Page Components

| Component | Status | Data Source | Props Received | Issues |
|-----------|--------|-------------|-----------------|--------|
| **LiveCockpit.tsx** | ⚠️ Partial | Supabase events | `events`, `currentDecision` | Data structure mismatch |
| **BeliefsConstraints.tsx** | ⚠️ Partial | Supabase beliefs | Via `LiveCockpitComplete` | May work - beliefs in payload |
| **SignalsBoard.tsx** | ❌ Not Wired | Mock | `mockData` passed in | No connection to live data |
| **TradesAttribution.tsx** | ❌ Not Wired | Mock | `mockData` passed in | No `trades` data fetched |
| **LearningConsole.tsx** | ❌ Not Wired | Mock | Mock only | Attribution data still mocked |
| **ExecutionQualityPage.tsx** | ❌ Not Wired | Mock | Mock only | No DVS/EQS data connected |
| **ParameterStudio.tsx** | ❌ Not Wired | Mock | Mock only | Control panel not wired |
| **ReplayLab.tsx** | ❌ Not Wired | Mock | Mock only | Historical queries missing |

### Data Flow Issues

1. **LiveCockpitComplete** receives:
   - ✅ `events`: From Supabase (but structure mismatch)
   - ✅ `currentBeliefs`: From Supabase
   - ❌ `driftAlerts`: Still `mockDriftAlerts`
   - ❌ `attribution`: Still `mockAttribution`
   - ❌ `executionBlame`: Still `mockExecutionBlame`
   - ❌ `manualActions`: Still `mockManualActions`
   - ❌ `dataQuality`: Still `mockDataQuality`
   - ❌ `marketData`: Still `mockMarketData` (no live IBKR data)

2. **Trade Data**: 
   - ❌ No `fetchRecentTrades()` call in App.tsx
   - ❌ `trades` parameter still passed as empty/mock
   - ❌ TradesAttribution component will have no data

3. **Signals Data**:
   - ❌ No `fetchEventsByType('SIGNALS_1M')` implemented
   - ❌ SignalsBoard component receives no data

---

## Data Sources Status

### Supabase Integration
- ✅ Connection configured (VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY set in Netlify)
- ✅ Queries created for basic operations
- ✅ Real-time subscriptions set up
- ❓ **Unknown**: Is bot actually pushing data to Supabase?
- ❓ **Unknown**: Are Supabase Realtime policies configured correctly?

### IBKR Live Data
- ❌ No `marketData` (price, change, volume) from IBKR
- ❌ MarketData component will show mock data only
- ❌ No live bar updates visible

### Mock Data Fallback
- ✅ Working when `VITE_DATA_SOURCE=mock`
- ❌ Incomplete when attempting Supabase (`VITE_DATA_SOURCE=supabase`)

---

## Component-by-Component Status

### ✅ LiveCockpit
- Receives `events` and `currentDecision` from App.tsx
- **Issue**: Event structure mismatch (missing severity, summary, reason_codes)
- **Fix Needed**: Transform Supabase events to match Event interface

### ❌ BeliefsConstraints
- Passed `beliefs` data via props
- **Issue**: Beliefs data structure likely doesn't match expected format
- **Fix Needed**: Verify beliefs payload structure from `BELIEFS_1M` events

### ❌ SignalsBoard
- **Issue**: Never receives `signals` prop
- **Current**: Still renders mock data from previous session
- **Fix Needed**: 
  - Add `fetchEventsByType('SIGNALS_1M')` query
  - Pass signals to SignalsBoard in App.tsx
  - Transform event payloads to Signal interface

### ❌ TradesAttribution
- **Issue**: Never receives `trades` prop from Supabase
- **Current**: Shows mock data only
- **Fix Needed**:
  - Call `fetchRecentTrades()` in App.tsx
  - Subscribe to trades table updates
  - Pass trades to component

### ❌ LearningConsole
- **Issue**: Attribution data still mocked
- **Fix Needed**:
  - Extract ATTRIBUTION_V2 events from live events
  - Transform to attribution format
  - Pass to component

### ❌ ExecutionQualityPage
- **Issue**: DVS/EQS metrics still mocked
- **Fix Needed**:
  - Add DVS_EQS_UPDATED event handling
  - Calculate or fetch quality metrics
  - Pass to component

### ⚠️  ParameterStudio
- **Issue**: Read-only in current implementation
- **Future**: Control panel requires mutation functions (write to Supabase)
- **Note**: Can wait for Phase 2

### ❌ ReplayLab
- **Issue**: No historical data queries
- **Fix Needed**:
  - Implement date-range queries
  - Add event filtering by date
  - Support strategy replay from historical data

---

## Root Cause Analysis

### Why UI Still Shows Mock Data Even With `VITE_DATA_SOURCE=supabase`

1. **Local Development**: `.env` has `VITE_DATA_SOURCE=mock` 
   - Local UI uses mock data by design
   
2. **Netlify Deployment**: Just now configured with `VITE_DATA_SOURCE=supabase`
   - Build is downloading now
   - Once deployed, will attempt Supabase fetch
   - **But**: Will fail due to data structure mismatches

3. **Bot Data Flow**: Unknown if working
   - SQLite → Publisher → Supabase: Not verified
   - May not have recent data to fetch

---

## Verification Checklist

### Before Declaring "Live Data Working"
- [ ] Verify bot is running and publishing to SQLite
- [ ] Check publisher.py is configured with Supabase credentials
- [ ] Query Supabase events table - should have recent events
- [ ] Fix Event interface data structure mismatch
- [ ] Test App.tsx data fetching in browser console
- [ ] Verify no TypeScript errors in Netlify build
- [ ] Check Supabase Realtime is enabled on events/trades tables
- [ ] Verify RLS policies allow anonymous read access
- [ ] Test real-time subscriptions update UI
- [ ] Verify all 8 components receive correct data

---

## Next Steps (Priority Order)

### CRITICAL (Required for any live data)
1. **Verify bot→Supabase data flow**
   - Confirm events table has recent data
   - Check event structure matches Supabase schema
   
2. **Fix Event structure mismatch**
   - Either update Supabase migration to include severity/summary/reason_codes
   - Or transform events in App.tsx to add missing fields from payload

3. **Fix remaining mock data in App.tsx**
   - Stop passing `mockMarketData` - fetch from IBKR
   - Stop passing `mockDriftAlerts` - extract from events
   - Stop passing `mockAttribution` - extract from ATTRIBUTION_V2 events
   - Fetch actual `trades` from Supabase

### HIGH (Phase 1 - Core Components)
4. Wire SignalsBoard to fetchEventsByType('SIGNALS_1M')
5. Wire TradesAttribution to fetchRecentTrades()
6. Wire LearningConsole to attribution events
7. Handle real-time updates via subscriptions

### MEDIUM (Phase 2)
8. Connect ExecutionQualityPage to DVS/EQS events
9. Implement ReplayLab historical queries
10. Implement ParameterStudio mutation functions

---

## Technical Debt

- [ ] Market data not sourced from IBKR - still mocked
- [ ] Multiple event types need transformation (SIGNALS, ATTRIBUTION, DVS_EQS)
- [ ] No error boundaries in components
- [ ] No loading/empty states for components without data
- [ ] Type safety gaps (event payloads are `any`)
- [ ] No connection status indication in all components

---

## Recommendations

### Immediate Action
Check if the bot is actually running and pushing data to Supabase. The entire live data system depends on this.

```bash
# In trading-bot-v1 root:
# 1. Check SQLite for recent events
# 2. Check publisher.py configuration
# 3. Query Supabase dashboard directly
```

### If No Data in Supabase
- Run bot locally with publisher enabled
- Monitor publisher.py logs
- Verify database credentials in publisher

### If Data Exists
- Deploy UI to Netlify with latest build
- Open browser DevTools
- Check App.tsx useEffect - should fetch events
- Verify no network errors to Supabase
- Check transformed event data structure

---

## Summary

**The UI infrastructure is in place**, but the data system is not fully integrated. The main blockers are:

1. **Data structure mismatches** - Components expect fields Supabase doesn't provide
2. **Incomplete event data** - Only the first two components are partially wired
3. **Unknown bot status** - No verification that bot is publishing to Supabase

Once these are resolved, real-time data flow should work.
