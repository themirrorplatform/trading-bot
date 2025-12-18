import { useEffect } from 'react';
import { useBotStore } from '../stores/botStore';
import { HealthMonitor } from '../components/HealthMonitor';
import { SnapshotView } from '../components/SnapshotView';
import { Timeline } from '../components/Timeline';
import { supabase } from '../lib/supabase';

interface DashboardProps {
  onLogout: () => void;
}

export function Dashboard({ onLogout }: DashboardProps) {
  const { subscribeToEvents, subscribeToSnapshot, subscribeToHealth, setLoading } = useBotStore();

  useEffect(() => {
    // Set up all subscriptions
    const unsubEvents = subscribeToEvents();
    const unsubSnapshot = subscribeToSnapshot();
    const unsubHealth = subscribeToHealth();

    setLoading(false);

    // Cleanup subscriptions on unmount
    return () => {
      unsubEvents();
      unsubSnapshot();
      unsubHealth();
    };
  }, [subscribeToEvents, subscribeToSnapshot, subscribeToHealth, setLoading]);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    onLogout();
  };

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: '#0a0a0a',
      color: '#ffffff',
      padding: '2rem',
    }}>
      <div style={{
        maxWidth: '1400px',
        margin: '0 auto',
      }}>
        <header style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '2rem',
          paddingBottom: '1rem',
          borderBottom: '1px solid #333',
        }}>
          <h1 style={{ fontSize: '2rem', fontWeight: 'bold' }}>
            Trading Bot Cockpit
          </h1>
          <button
            onClick={handleLogout}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#2a2a2a',
              color: '#ffffff',
              border: '1px solid #444',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.875rem',
            }}
          >
            Logout
          </button>
        </header>

        <div style={{
          display: 'grid',
          gap: '1.5rem',
        }}>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
            gap: '1.5rem',
          }}>
            <HealthMonitor />
            <SnapshotView />
          </div>

          <Timeline />
        </div>

        <footer style={{
          marginTop: '2rem',
          paddingTop: '1rem',
          borderTop: '1px solid #333',
          textAlign: 'center',
          color: '#888',
          fontSize: '0.875rem',
        }}>
          <p>
            Read-only monitoring • Cloud mode •{' '}
            App mode: {import.meta.env.VITE_APP_MODE || 'cloud'}
          </p>
        </footer>
      </div>
    </div>
  );
}
