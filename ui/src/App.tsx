import { useEffect, useState } from 'react';
import { Auth } from './components/Auth';
import { Dashboard } from './pages/Dashboard';
import { supabase } from './lib/supabase';
import { useBotStore } from './stores/botStore';

export function App() {
  const [session, setSession] = useState<unknown | null>(null);
  const [loading, setLoading] = useState(true);
  const { setAuthenticated } = useBotStore();

  useEffect(() => {
    // Check active session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setAuthenticated(!!session);
      setLoading(false);
    });

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setAuthenticated(!!session);
    });

    return () => subscription.unsubscribe();
  }, [setAuthenticated]);

  if (loading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '100vh',
          backgroundColor: '#0a0a0a',
          color: '#ffffff',
        }}
      >
        <div style={{ textAlign: 'center' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              border: '4px solid #333',
              borderTop: '4px solid #0070f3',
              borderRadius: '50%',
              margin: '0 auto 1rem',
              animation: 'spin 1s linear infinite',
            }}
          />
          <p>Loading...</p>
        </div>
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  if (!session) {
    return <Auth onAuthSuccess={() => setSession(true)} />;
  }

  return <Dashboard onLogout={() => setSession(null)} />;
}
