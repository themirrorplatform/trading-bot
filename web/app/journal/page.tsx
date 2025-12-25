import { createClient } from '@/lib/supabase/server'
import { format } from 'date-fns'

export const revalidate = 10

async function getJournalEntries() {
  const supabase = createClient()

  const { data } = await supabase
    .from('decision_journal')
    .select('*')
    .order('timestamp', { ascending: false })
    .limit(100)

  return data || []
}

export default async function JournalPage() {
  const entries = await getJournalEntries()

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Decision Journal</h1>
        <div className="flex gap-2 text-sm">
          <select className="bg-slate-700 rounded px-3 py-1.5">
            <option>All Actions</option>
            <option>ENTER Only</option>
            <option>SKIP Only</option>
          </select>
          <input
            type="date"
            className="bg-slate-700 rounded px-3 py-1.5"
            defaultValue={new Date().toISOString().split('T')[0]}
          />
        </div>
      </div>

      <div className="space-y-4">
        {entries.length === 0 ? (
          <div className="card text-center text-slate-500 py-12">
            No journal entries yet. Run the bot to generate decision logs.
          </div>
        ) : (
          entries.map((entry: any) => (
            <div
              key={entry.id}
              className={`card border-l-4 ${
                entry.action === 'ENTER'
                  ? 'border-l-emerald-500'
                  : 'border-l-slate-500'
              }`}
            >
              <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-3">
                  <span
                    className={`px-2 py-0.5 text-xs rounded ${
                      entry.action === 'ENTER'
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : 'bg-slate-500/20 text-slate-400'
                    }`}
                  >
                    {entry.action}
                  </span>
                  <span className="text-sm text-slate-400">
                    {format(new Date(entry.timestamp), 'MMM d, yyyy HH:mm:ss')}
                  </span>
                </div>
                {entry.euc_score && (
                  <span className="text-sm font-mono">
                    EUC: {entry.euc_score.toFixed(3)}
                  </span>
                )}
              </div>

              <p className="text-slate-200 mb-3">{entry.plain_english}</p>

              <div className="flex flex-wrap gap-2 text-xs">
                {entry.setup_scores &&
                  Object.entries(entry.setup_scores as Record<string, number>).map(
                    ([key, value]) => (
                      <span
                        key={key}
                        className={`px-2 py-0.5 rounded ${
                          value >= 0.65
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : value >= 0.5
                            ? 'bg-yellow-500/20 text-yellow-400'
                            : 'bg-slate-500/20 text-slate-400'
                        }`}
                      >
                        {key}: {(value as number).toFixed(2)}
                      </span>
                    )
                  )}
              </div>

              {entry.context && (
                <div className="mt-3 pt-3 border-t border-slate-700 text-xs text-slate-500 flex gap-4">
                  <span>DVS: {(entry.context as any).dvs?.toFixed(2)}</span>
                  <span>EQS: {(entry.context as any).eqs?.toFixed(2)}</span>
                  <span>Phase: {(entry.context as any).session_phase}</span>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
