import { useBotStore } from '../stores/botStore';

export function SnapshotView() {
  const snapshot = useBotStore((state) => state.snapshot);

  if (!snapshot) {
    return (
      <div style={{
        padding: '1rem',
        backgroundColor: '#1a1a1a',
        borderRadius: '8px',
        border: '1px solid #333',
      }}>
        <h2 style={{ marginBottom: '1rem' }}>Current Snapshot</h2>
        <p style={{ color: '#888' }}>No snapshot data available</p>
      </div>
    );
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(value);
  };

  return (
    <div style={{
      padding: '1rem',
      backgroundColor: '#1a1a1a',
      borderRadius: '8px',
      border: '1px solid #333',
    }}>
      <h2 style={{ marginBottom: '1rem' }}>Current Snapshot</h2>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
        <div>
          <div style={{ color: '#888', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
            Equity
          </div>
          <div style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>
            {formatCurrency(snapshot.equity)}
          </div>
        </div>

        <div>
          <div style={{ color: '#888', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
            Position
          </div>
          <div style={{
            fontSize: '1.25rem',
            fontWeight: 'bold',
            color: snapshot.position > 0 ? '#10b981' : snapshot.position < 0 ? '#ef4444' : '#888',
          }}>
            {snapshot.position > 0 ? `+${snapshot.position}` : snapshot.position}
          </div>
        </div>

        <div>
          <div style={{ color: '#888', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
            Unrealized P&L
          </div>
          <div style={{
            fontSize: '1.25rem',
            fontWeight: 'bold',
            color: snapshot.unrealized_pnl >= 0 ? '#10b981' : '#ef4444',
          }}>
            {formatCurrency(snapshot.unrealized_pnl)}
          </div>
        </div>

        <div>
          <div style={{ color: '#888', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
            Realized P&L
          </div>
          <div style={{
            fontSize: '1.25rem',
            fontWeight: 'bold',
            color: snapshot.realized_pnl >= 0 ? '#10b981' : '#ef4444',
          }}>
            {formatCurrency(snapshot.realized_pnl)}
          </div>
        </div>

        <div>
          <div style={{ color: '#888', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
            Daily P&L
          </div>
          <div style={{
            fontSize: '1.25rem',
            fontWeight: 'bold',
            color: snapshot.daily_pnl >= 0 ? '#10b981' : '#ef4444',
          }}>
            {formatCurrency(snapshot.daily_pnl)}
          </div>
        </div>

        <div>
          <div style={{ color: '#888', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
            Last Update
          </div>
          <div style={{ fontSize: '0.875rem' }}>
            {new Date(snapshot.timestamp).toLocaleTimeString()}
          </div>
        </div>
      </div>
    </div>
  );
}
