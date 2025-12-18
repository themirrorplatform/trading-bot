import { useBotStore } from '../stores/botStore';

export function HealthMonitor() {
  const health = useBotStore((state) => state.health);

  if (!health) {
    return (
      <div style={{
        padding: '1rem',
        backgroundColor: '#1a1a1a',
        borderRadius: '8px',
        border: '1px solid #333',
      }}>
        <h2 style={{ marginBottom: '1rem' }}>Bot Health</h2>
        <p style={{ color: '#888' }}>No health data available</p>
      </div>
    );
  }

  const statusColor = {
    healthy: '#10b981',
    degraded: '#f59e0b',
    down: '#ef4444',
  }[health.status];

  return (
    <div style={{
      padding: '1rem',
      backgroundColor: '#1a1a1a',
      borderRadius: '8px',
      border: '1px solid #333',
    }}>
      <h2 style={{ marginBottom: '1rem' }}>Bot Health</h2>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
        <div>
          <div style={{ color: '#888', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
            Status
          </div>
          <div style={{ color: statusColor, fontWeight: 'bold', textTransform: 'uppercase' }}>
            {health.status}
          </div>
        </div>

        <div>
          <div style={{ color: '#888', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
            Device ID
          </div>
          <div>{health.device_id}</div>
        </div>

        <div>
          <div style={{ color: '#888', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
            DVS (Data Validity Score)
          </div>
          <div style={{ color: health.dvs >= 0.80 ? '#10b981' : '#ef4444' }}>
            {(health.dvs * 100).toFixed(1)}%
          </div>
        </div>

        <div>
          <div style={{ color: '#888', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
            EQS (Execution Quality Score)
          </div>
          <div style={{ color: health.eqs >= 0.75 ? '#10b981' : '#ef4444' }}>
            {(health.eqs * 100).toFixed(1)}%
          </div>
        </div>

        <div>
          <div style={{ color: '#888', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
            Kill Switch
          </div>
          <div style={{ color: health.kill_switch_active ? '#ef4444' : '#10b981' }}>
            {health.kill_switch_active ? 'ACTIVE' : 'Inactive'}
          </div>
        </div>

        <div>
          <div style={{ color: '#888', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
            Last Heartbeat
          </div>
          <div style={{ fontSize: '0.875rem' }}>
            {new Date(health.last_heartbeat).toLocaleTimeString()}
          </div>
        </div>
      </div>
    </div>
  );
}
