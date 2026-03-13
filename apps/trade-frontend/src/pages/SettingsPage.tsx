import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Lock, Plus, X, Search, Settings } from 'lucide-react';
import {
  login,
  verifyAuth,
  fetchWatchlist,
  addWatchlistSymbol,
  removeWatchlistSymbol,
  fetchAllSymbols,
} from '../api/client';

function getToken(): string | null {
  return localStorage.getItem('settings_token');
}

function setToken(token: string) {
  localStorage.setItem('settings_token', token);
}

function clearToken() {
  localStorage.removeItem('settings_token');
}

// --- Login Form ---
function LoginForm({ onSuccess }: { onSuccess: () => void }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const data = await login(password);
      setToken(data.access_token);
      onSuccess();
    } catch {
      setError('Wrong password');
    }
  };

  return (
    <div style={{ maxWidth: 400, margin: '80px auto', padding: 24 }}>
      <div style={{
        background: 'var(--bg-surface)',
        borderRadius: 12,
        border: '1px solid var(--border-subtle)',
        padding: 32,
      }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Lock size={32} style={{ color: 'var(--accent-primary)', marginBottom: 8 }} />
          <h2 style={{ color: 'var(--text-primary)', fontSize: 'var(--text-xl)', fontWeight: 'var(--font-semibold)' }}>Settings</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', marginTop: 4 }}>Enter password to continue</p>
        </div>
        <form onSubmit={handleSubmit}>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            autoFocus
            style={{
              width: '100%',
              padding: '10px 14px',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-default)',
              borderRadius: 8,
              color: 'var(--text-primary)',
              fontSize: 'var(--text-base)',
              outline: 'none',
              boxSizing: 'border-box',
            }}
          />
          {error && <p style={{ color: 'var(--color-danger)', fontSize: 'var(--text-sm)', marginTop: 8 }}>{error}</p>}
          <button
            type="submit"
            style={{
              width: '100%',
              marginTop: 16,
              padding: '10px 0',
              background: 'var(--accent-primary)',
              color: '#050507',
              border: 'none',
              borderRadius: 8,
              fontSize: 'var(--text-base)',
              fontWeight: 'var(--font-semibold)',
              cursor: 'pointer',
            }}
          >
            Login
          </button>
        </form>
      </div>
    </div>
  );
}

// --- Watchlist Manager ---
function WatchlistManager() {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');

  const { data: watchlist = [], isLoading } = useQuery({
    queryKey: ['watchlist'],
    queryFn: fetchWatchlist,
  });

  const { data: allSymbolsData } = useQuery({
    queryKey: ['allSymbols'],
    queryFn: fetchAllSymbols,
    staleTime: 60_000,
  });

  const addMutation = useMutation({
    mutationFn: addWatchlistSymbol,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist'] });
      setSearchTerm('');
    },
  });

  const removeMutation = useMutation({
    mutationFn: removeWatchlistSymbol,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['watchlist'] }),
  });

  // Build symbol suggestions from /analysis/symbols
  const allSymbols: string[] = (allSymbolsData ?? []).map((s: { symbol: string }) => s.symbol);
  const filtered = searchTerm.length >= 2
    ? allSymbols.filter(
        (s: string) => s.includes(searchTerm.toUpperCase()) && !watchlist.includes(s)
      ).slice(0, 8)
    : [];

  return (
    <div style={{ maxWidth: 600, margin: '32px auto', padding: '0 16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <Settings size={24} style={{ color: 'var(--accent-primary)' }} />
        <h1 style={{ color: 'var(--text-primary)', fontSize: 'var(--text-xl)', fontWeight: 'var(--font-semibold)', margin: 0 }}>
          Watchlist
        </h1>
        <span style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-sm)' }}>
          Alert only these symbols
        </span>
      </div>

      {/* Info banner */}
      <div style={{
        background: 'var(--accent-muted)',
        border: '1px solid var(--border-accent)',
        borderRadius: 8,
        padding: '12px 16px',
        marginBottom: 20,
        fontSize: 'var(--text-sm)',
        color: 'var(--text-secondary)',
        lineHeight: 1.5,
      }}>
        Watchlist empty = all alerts OFF. Add symbols to receive Telegram alerts for only those symbols.
      </div>

      {/* Search + Add */}
      <div style={{ position: 'relative', marginBottom: 20 }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          borderRadius: 8,
          padding: '8px 12px',
        }}>
          <Search size={16} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search symbol (e.g. BTC)"
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              color: 'var(--text-primary)',
              fontSize: 'var(--text-base)',
              outline: 'none',
            }}
          />
        </div>
        {/* Suggestions dropdown */}
        {filtered.length > 0 && (
          <div style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            marginTop: 4,
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-default)',
            borderRadius: 8,
            overflow: 'hidden',
            zIndex: 10,
            boxShadow: 'var(--shadow-md)',
          }}>
            {filtered.map((symbol: string) => (
              <button
                key={symbol}
                onClick={() => addMutation.mutate(symbol)}
                disabled={addMutation.isPending}
                style={{
                  width: '100%',
                  padding: '10px 16px',
                  background: 'transparent',
                  border: 'none',
                  borderBottom: '1px solid var(--border-subtle)',
                  color: 'var(--text-primary)',
                  fontSize: 'var(--text-sm)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  textAlign: 'left',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-overlay)')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
              >
                <span style={{ fontWeight: 'var(--font-medium)' }}>{symbol}</span>
                <Plus size={14} style={{ color: 'var(--accent-primary)' }} />
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Watchlist items */}
      <div style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 12,
        overflow: 'hidden',
      }}>
        {isLoading ? (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-tertiary)' }}>Loading...</div>
        ) : watchlist.length === 0 ? (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 'var(--text-sm)' }}>
            No symbols added. Alerts are OFF.
          </div>
        ) : (
          watchlist.map((symbol: string, idx: number) => (
            <div
              key={symbol}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px 16px',
                borderBottom: idx < watchlist.length - 1 ? '1px solid var(--border-subtle)' : 'none',
              }}
            >
              <span style={{ color: 'var(--text-primary)', fontSize: 'var(--text-base)', fontWeight: 'var(--font-medium)' }}>
                {symbol}
              </span>
              <button
                onClick={() => removeMutation.mutate(symbol)}
                disabled={removeMutation.isPending}
                style={{
                  background: 'var(--color-danger-muted)',
                  border: 'none',
                  borderRadius: 6,
                  padding: '4px 8px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  color: 'var(--color-danger)',
                }}
              >
                <X size={14} />
              </button>
            </div>
          ))
        )}
      </div>

      {/* Count */}
      {watchlist.length > 0 && (
        <p style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-xs)', marginTop: 8, textAlign: 'right' }}>
          {watchlist.length} symbol{watchlist.length !== 1 ? 's' : ''} watching
        </p>
      )}

      {/* Logout */}
      <div style={{ marginTop: 32, textAlign: 'center' }}>
        <button
          onClick={() => { clearToken(); window.location.reload(); }}
          style={{
            background: 'transparent',
            border: '1px solid var(--border-default)',
            borderRadius: 8,
            padding: '8px 20px',
            color: 'var(--text-secondary)',
            fontSize: 'var(--text-sm)',
            cursor: 'pointer',
          }}
        >
          Logout
        </button>
      </div>
    </div>
  );
}

// --- Main Settings Page ---
export default function SettingsPage() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setAuthenticated(false);
      return;
    }
    verifyAuth()
      .then(() => setAuthenticated(true))
      .catch(() => {
        clearToken();
        setAuthenticated(false);
      });
  }, []);

  if (authenticated === null) return null;
  if (!authenticated) return <LoginForm onSuccess={() => setAuthenticated(true)} />;
  return <WatchlistManager />;
}
