import { useBotStore } from '../stores/botStore';

export function Timeline() {
  const events = useBotStore((state) => state.events);

  return (
    <div style={{
      padding: '1rem',
      backgroundColor: '#1a1a1a',
      borderRadius: '8px',
      border: '1px solid #333',
    }}>
      <h2 style={{ marginBottom: '1rem' }}>Event Timeline</h2>
      
      {events.length === 0 ? (
        <p style={{ color: '#888' }}>No events yet. Waiting for bot activity...</p>
      ) : (
        <div style={{
          maxHeight: '400px',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.75rem',
        }}>
          {events.map((event) => (
            <div
              key={event.id}
              style={{
                padding: '0.75rem',
                backgroundColor: '#2a2a2a',
                borderRadius: '4px',
                border: '1px solid #444',
              }}
            >
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '0.5rem',
              }}>
                <span style={{
                  fontWeight: 'bold',
                  color: getEventTypeColor(event.event_type),
                }}>
                  {event.event_type}
                </span>
                <span style={{ fontSize: '0.875rem', color: '#888' }}>
                  {new Date(event.timestamp).toLocaleTimeString()}
                </span>
              </div>
              
              <div style={{
                fontSize: '0.875rem',
                color: '#ccc',
                fontFamily: 'monospace',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                maxHeight: '100px',
                overflowY: 'auto',
              }}>
                {sanitizePayload(event.payload)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function sanitizePayload(payload: Record<string, unknown>): string {
  try {
    // Create a safe copy without potential script tags or dangerous content
    const safeCopy = JSON.parse(JSON.stringify(payload));
    return JSON.stringify(safeCopy, null, 2);
  } catch {
    return 'Invalid payload data';
  }
}

function getEventTypeColor(eventType: string): string {
  if (eventType.includes('ORDER')) return '#3b82f6';
  if (eventType.includes('FILL')) return '#10b981';
  if (eventType.includes('ERROR')) return '#ef4444';
  if (eventType.includes('SIGNAL')) return '#8b5cf6';
  if (eventType.includes('DECISION')) return '#f59e0b';
  return '#6b7280';
}
