import { useState } from 'react';
import { supabase } from '../lib/supabase';

interface AuthProps {
  onAuthSuccess: () => void;
}

export function Auth({ onAuthSuccess }: AuthProps) {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      setLoading(true);
      setMessage(null);
      
      const { error } = await supabase.auth.signInWithOtp({
        email,
        options: {
          emailRedirectTo: window.location.origin,
        },
      });

      if (error) throw error;

      setMessage({
        type: 'success',
        text: 'Check your email for the magic link!',
      });
    } catch (error) {
      setMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'An error occurred',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      backgroundColor: '#0a0a0a',
      color: '#ffffff',
    }}>
      <div style={{
        maxWidth: '400px',
        width: '100%',
        padding: '2rem',
        backgroundColor: '#1a1a1a',
        borderRadius: '8px',
        border: '1px solid #333',
      }}>
        <h1 style={{ marginBottom: '1.5rem', textAlign: 'center' }}>
          Trading Bot Cockpit
        </h1>
        
        <form onSubmit={handleLogin}>
          <div style={{ marginBottom: '1rem' }}>
            <label htmlFor="email" style={{ display: 'block', marginBottom: '0.5rem' }}>
              Email Address
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              disabled={loading}
              style={{
                width: '100%',
                padding: '0.75rem',
                backgroundColor: '#2a2a2a',
                border: '1px solid #444',
                borderRadius: '4px',
                color: '#ffffff',
                fontSize: '1rem',
              }}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              padding: '0.75rem',
              backgroundColor: loading ? '#555' : '#0070f3',
              color: '#ffffff',
              border: 'none',
              borderRadius: '4px',
              fontSize: '1rem',
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'background-color 0.2s',
            }}
          >
            {loading ? 'Sending...' : 'Send Magic Link'}
          </button>
        </form>

        {message && (
          <div
            style={{
              marginTop: '1rem',
              padding: '0.75rem',
              backgroundColor: message.type === 'success' ? '#1a4d2e' : '#4d1a1a',
              border: `1px solid ${message.type === 'success' ? '#2d6a3e' : '#6a2d2d'}`,
              borderRadius: '4px',
              fontSize: '0.875rem',
            }}
          >
            {message.text}
          </div>
        )}

        <p style={{
          marginTop: '1.5rem',
          fontSize: '0.875rem',
          color: '#888',
          textAlign: 'center',
        }}>
          We'll send you a magic link for passwordless login.
        </p>
      </div>
    </div>
  );
}
