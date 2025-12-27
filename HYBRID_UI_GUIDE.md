# Hybrid UI Implementation - Complete Guide

## ✅ What's Done

### 1. Typed Supabase Client
- **File**: `ui/src/lib/supabase/types.ts` - Database schema types from web/
- **File**: `ui/src/lib/supabase.ts` - Updated with typed client

### 2. Data Access Layer
- **File**: `ui/src/lib/data/queries.ts` - All read operations
- **File**: `ui/src/lib/data/realtime.ts` - Realtime subscriptions
- **File**: `ui/src/lib/data/config.ts` - Feature flag for mock vs live

### 3. Feature Flag System
- **File**: `ui/.env` - Set `VITE_DATA_SOURCE=mock` or `supabase`
- Mock data: Works today, no backend required
- Live data: Connects to your deployed Supabase

### 4. React Hook for Live Data
- **File**: `ui/src/hooks/useLiveCockpitData.ts` - Auto-switching hook

---

## 🔌 How to Wire a Component to Live Data

### Example: Converting App.tsx to use live data

**BEFORE (Mock Data):**
```tsx
import { mockCompleteEvents, mockSkipDecision } from './data/mockData';

export default function App() {
  const [events] = useState(mockCompleteEvents);
  const [decision] = useState(mockSkipDecision);
  
  return <LiveCockpit events={events} currentDecision={decision} />;
}
```

**AFTER (Live Data with Fallback):**
```tsx
import { useLiveCockpitData } from './hooks/useLiveCockpitData';

export default function App() {
  const { events, currentDecision, loading, isLive } = useLiveCockpitData({
    streamId: 'MES_RTH',
    pollInterval: 5000, // Poll every 5 seconds as fallback
  });
  
  return (
    <>
      {loading && <div>Loading...</div>}
      {isLive && <div className="status">🟢 LIVE</div>}
      <LiveCockpit events={events} currentDecision={currentDecision} />
    </>
  );
}
```

That's it. The hook handles:
- ✅ Feature flag checking (mock vs live)
- ✅ Initial data fetch
- ✅ Realtime subscriptions
- ✅ Fallback polling
- ✅ Cleanup on unmount

---

## 📊 Wiring Other Pages

### SignalsBoard
```tsx
import { fetchEventsByType } from '../lib/data/queries';

useEffect(() => {
  if (isUsingLiveData()) {
    fetchEventsByType('MES_RTH', 'SIGNALS_1M', 1).then(data => {
      if (data.length > 0) {
        setSignals(data[0].payload);
      }
    });
  }
}, []);
```

### TradesAttribution
```tsx
import { fetchRecentTrades, subscribeToTrades } from '../lib/data/queries';

useEffect(() => {
  if (isUsingLiveData()) {
    fetchRecentTrades('MES_RTH', 20).then(setTrades);
    
    const channel = subscribeToTrades('MES_RTH', (newTrade) => {
      setTrades(prev => [newTrade, ...prev]);
    });
    
    return () => unsubscribe(channel);
  }
}, []);
```

### LearningConsole
```tsx
import { fetchEventsByType } from '../lib/data/queries';

useEffect(() => {
  if (isUsingLiveData()) {
    fetchEventsByType('MES_RTH', 'ATTRIBUTION', 50).then(setAttributions);
  }
}, []);
```

---

## 🚀 Deployment Steps

### 1. Test Locally with Mock Data
```bash
cd ui
npm install
npm run dev
```
Should work immediately with mock data.

### 2. Test Locally with Live Data
```bash
# In ui/.env, change:
VITE_DATA_SOURCE=supabase

npm run dev
```
Should connect to your Supabase and show real events (if bot is running).

### 3. Build for Netlify
```bash
npm run build
```
Creates `ui/dist/` directory.

### 4. Deploy to Netlify

**Option A: Netlify CLI**
```bash
npm install -g netlify-cli
netlify deploy --prod --dir=dist
```

**Option B: Netlify Dashboard**
1. Go to https://app.netlify.com
2. "Add new site" → "Import an existing project"
3. Connect your GitHub repo
4. Build settings:
   - **Base directory**: `ui`
   - **Build command**: `npm run build`
   - **Publish directory**: `ui/dist`
5. Environment variables:
   - `VITE_SUPABASE_URL`: `https://hhyilmbejidzriljesph.supabase.co`
   - `VITE_SUPABASE_ANON_KEY`: `eyJhbGci...` (your anon key)
   - `VITE_DATA_SOURCE`: `supabase`
   - `VITE_STREAM_ID`: `MES_RTH`
6. Deploy!

---

## 🔐 Security Notes

### ✅ Safe in Browser
- Anon key: Yes (has RLS protection)
- Supabase URL: Yes (public)

### ❌ Never in Browser
- Service role key: NO
- Database password: NO
- API secrets: NO

### RLS Protection
Your Supabase migrations already set up RLS. Make sure policies allow:
- **Read**: Anyone can read events (or restrict by device_id if needed)
- **Write**: Only authenticated service accounts (bot publisher)

---

## 🎯 Control Panel Actions

For "LiveCockpit as control panel" (kill switch, gate toggles, parameter tuning):

### Option 1: Edge Functions (Recommended)
```typescript
// supabase/functions/toggle-kill-switch/index.ts
import { createClient } from '@supabase/supabase-js'

Deno.serve(async (req) => {
  const { action, reason } = await req.json()
  
  // Insert KILL_SWITCH event
  const supabase = createClient(...)
  await supabase.from('events').insert({
    stream_id: 'MES_RTH',
    event_type: 'KILL_SWITCH',
    payload: { action, reason },
    ...
  })
  
  return new Response(JSON.stringify({ ok: true }))
})
```

Call from UI:
```tsx
const toggleKillSwitch = async () => {
  await fetch(`${supabaseUrl}/functions/v1/toggle-kill-switch`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${supabaseAnonKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ action: 'TRIGGER', reason: 'Manual halt' })
  })
}
```

### Option 2: Supabase RPC
```sql
-- In a migration:
CREATE OR REPLACE FUNCTION trigger_kill_switch(
  p_stream_id TEXT,
  p_reason TEXT
) RETURNS VOID AS $$
BEGIN
  INSERT INTO events (stream_id, event_type, payload, ...)
  VALUES (p_stream_id, 'KILL_SWITCH', jsonb_build_object('reason', p_reason), ...);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION trigger_kill_switch TO anon;
```

Call from UI:
```tsx
await supabase.rpc('trigger_kill_switch', {
  p_stream_id: 'MES_RTH',
  p_reason: 'Manual halt'
})
```

---

## 📈 Next Steps (Incremental)

1. **Week 1**: Deploy with mock data to verify build/deploy works
2. **Week 2**: Wire one page (LiveCockpit) to live data
3. **Week 3**: Add realtime for event stream
4. **Week 4**: Wire remaining pages (Signals, Trades, Learning)
5. **Week 5**: Add control panel actions (kill switch, gates)
6. **Week 6**: Add Postgres views for heavy aggregates

---

## ❓ FAQ

**Q: Can I test locally without running the bot?**
A: Yes, set `VITE_DATA_SOURCE=mock` in .env

**Q: How do I know if realtime is working?**
A: Check browser console for "SUBSCRIBED" message. Also check Supabase dashboard → Database → Replication

**Q: What if events table is empty?**
A: Run your bot's publisher.py to push events to Supabase, or seed test data

**Q: Do I need to rewrite all 87 components?**
A: No! Only wire the top-level pages. Components stay the same.

**Q: What about SSR?**
A: Don't need it. Your cockpit is client-side + realtime. Use RPC/views for heavy queries.

---

## 🎉 Result

You now have:
- ✅ 87-component UI (unchanged, fully functional)
- ✅ Typed Supabase client
- ✅ Data access layer (no direct Supabase calls in components)
- ✅ Feature flag for mock vs live
- ✅ Realtime subscriptions
- ✅ Ready to deploy to Netlify
- ✅ Incremental migration path

**You can ship the UI TODAY with mock data, then flip the switch to go live when the bot is running.**
