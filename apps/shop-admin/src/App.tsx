import { useState, useEffect } from 'react';
import { ShieldAlert, Zap, Clock, Activity, Users, Tag, Power, AlertTriangle, Globe } from 'lucide-react';

interface SettingsData {
  mode: string;
  base_tps: number;
  chaos_mode: boolean;
  category_bias: string | null;
  user_persona_bias: string | null;
  expires_at: string | null;
}

const API_BASE = '/api/admin';

function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('admin_token'));
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');

  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [loading, setLoading] = useState(true);

  // Form states
  const [mode, setMode] = useState('normal');
  const [tps, setTps] = useState(100);
  const [chaos, setChaos] = useState(false);
  const [category, setCategory] = useState('');
  const [persona, setPersona] = useState('');
  const [duration, setDuration] = useState(0);

  const fetchSettings = async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/settings`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.status === 401) {
        setToken(null);
        localStorage.removeItem('admin_token');
        return;
      }
      const data: SettingsData = await res.json();
      setSettings(data);
      setMode(data.mode);
      setTps(data.base_tps);
      setChaos(data.chaos_mode);
      setCategory(data.category_bias || '');
      setPersona(data.user_persona_bias || '');
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchSettings();
  }, [token]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
      });

      if (!res.ok) throw new Error('Invalid Password');

      const data = await res.json();
      setToken(data.token);
      localStorage.setItem('admin_token', data.token);
      setLoginError('');
      setPassword('');
      setLoading(true);
    } catch (err) {
      setLoginError('Authentication Failed');
    }
  };

  const handleApply = async () => {
    try {
      const payload = {
        mode,
        base_tps: tps,
        chaos_mode: chaos,
        category_bias: category === '' ? null : category,
        user_persona_bias: persona === '' ? null : persona,
        duration_minutes: duration === 0 ? null : duration
      };

      const res = await fetch(`${API_BASE}/settings`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        alert('Configuration deployed successfully to Kafka streams!');
        fetchSettings();
      } else {
        alert('Failed to update config');
      }
    } catch (err) {
      console.error(err);
      alert('Network Error');
    }
  };

  const handleLogout = () => {
    setToken(null);
    localStorage.removeItem('admin_token');
  };

  if (!token) {
    return (
      <div className="app-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', width: '100vw' }}>
        <div className="glass-card" style={{ width: '400px', padding: '2rem', textAlign: 'center' }}>
          <div style={{ marginBottom: '2rem' }}>
            <ShieldAlert size={48} color="#ef4444" style={{ marginBottom: '1rem' }} />
            <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>Admin Gateway</h2>
            <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginTop: '0.5rem' }}>Restricted Access. Authentication Required.</p>
          </div>

          <form onSubmit={handleLogin}>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Enter Admin Passcode"
              style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', marginBottom: '1rem' }}
            />
            {loginError && <div style={{ color: '#ef4444', marginBottom: '1rem', fontSize: '0.9rem' }}>{loginError}</div>}
            <button type="submit" style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', background: '#3b82f6', color: 'white', fontWeight: 'bold', border: 'none', cursor: 'pointer' }}>
              Authenticate
            </button>
          </form>
        </div>
      </div>
    );
  }

  if (loading) return <div style={{ color: 'white', textAlign: 'center', marginTop: '20vh' }}>Loading Secure Context...</div>;

  return (
    <div className="app-container">
      <nav className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <Globe size={24} color="#8b5cf6" />
            <h1>Traffic<span style={{ color: '#8b5cf6' }}>Control</span></h1>
          </div>
        </div>
        <div className="nav-links">
          <button className="nav-item active">
            <Activity size={20} />
            <span>Generator Control</span>
          </button>
          <button className="nav-item" onClick={handleLogout} style={{ marginTop: 'auto', color: '#ef4444' }}>
            <Power size={20} />
            <span>Terminate Session</span>
          </button>
        </div>
      </nav>

      <main className="main-content">
        <div className="page-content" style={{ maxWidth: '900px', margin: '0 auto' }}>
          <div className="page-header" style={{ marginBottom: '2rem' }}>
            <h2>Real-Time Traffic Injection</h2>
            <p>Publish configuration overrides directly to the Kafka Topic bypassing standard generation.</p>
          </div>

          {settings?.expires_at && (
            <div className="glass-card" style={{ borderLeft: '4px solid #f59e0b', marginBottom: '2rem', padding: '1rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <Clock color="#f59e0b" />
              <div>
                <h4 style={{ margin: 0, color: '#f59e0b' }}>Time-Bound Override Active</h4>
                <p style={{ margin: 0, fontSize: '0.9rem', color: '#94a3b8' }}>Configuration will automatically revert to default normal traffic at {new Date(settings.expires_at).toLocaleTimeString()}</p>
              </div>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>

            <div className="glass-card">
              <h3 className="section-title"><Zap size={18} /> Global Mode</h3>
              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
                {['normal', 'sale', 'test'].map(m => (
                  <button
                    key={m}
                    onClick={() => setMode(m)}
                    style={{
                      flex: 1, padding: '0.5rem', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.1)', cursor: 'pointer',
                      background: mode === m ? '#3b82f6' : 'rgba(0,0,0,0.3)', color: 'white', textTransform: 'capitalize'
                    }}
                  >
                    {m}
                  </button>
                ))}
              </div>
              <p style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.5rem' }}>Sale mode multiplies traffic rate by 10x.</p>
            </div>

            <div className="glass-card">
              <h3 className="section-title"><Activity size={18} /> Base TPS Scaling</h3>
              <div style={{ marginTop: '1rem' }}>
                <input
                  type="range"
                  min="10" max="2000" step="10"
                  value={tps} onChange={e => setTps(parseInt(e.target.value))}
                  style={{ width: '100%', cursor: 'pointer', marginBottom: '0.5rem' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8' }}>
                  <span>{tps} Tx/sec</span>
                  <span style={{ background: 'rgba(59, 130, 246, 0.2)', color: '#60a5fa', padding: '2px 8px', borderRadius: '10px', fontSize: '0.8rem' }}>
                    Peak: {mode === 'sale' ? tps * 10 : tps} TPS
                  </span>
                </div>
              </div>
            </div>

            <div className="glass-card" style={{ border: chaos ? '1px solid rgba(239, 68, 68, 0.5)' : '' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 className="section-title" style={{ margin: 0, color: chaos ? '#ef4444' : '' }}><AlertTriangle size={18} /> Chaos Mode</h3>
                <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                  <input type="checkbox" checked={chaos} onChange={e => setChaos(e.target.checked)} style={{ marginRight: '0.5rem', width: '1.2rem', height: '1.2rem' }} />
                  <span style={{ color: chaos ? '#ef4444' : '#94a3b8' }}>{chaos ? 'ENGAGED' : 'OFF'}</span>
                </label>
              </div>
              <p style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.5rem' }}>Randomly drops packets, corrupts product categories, and simulates payment gateway failures.</p>
            </div>

            <div className="glass-card">
              <h3 className="section-title"><Tag size={18} /> Category Bias Injection</h3>
              <select value={category} onChange={e => setCategory(e.target.value)} style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', marginTop: '1rem' }}>
                <option value="">No Bias (Random Distribution)</option>
                <option value="electronics">Electronics (e.g. Apple Event)</option>
                <option value="fashion">Fashion (e.g. FW Collection)</option>
                <option value="beauty">Beauty</option>
                <option value="food">Food & Grocery</option>
                <option value="home">Home & Living</option>
              </select>
              <p style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.5rem' }}>Forces 70% of generation traffic into selected category.</p>
            </div>

            <div className="glass-card">
              <h3 className="section-title"><Users size={18} /> Persona targeting</h3>
              <select value={persona} onChange={e => setPersona(e.target.value)} style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', marginTop: '1rem' }}>
                <option value="">No Override (Natural Blend)</option>
                <option value="heavy_buyer">Whale Simulation (Heavy Buyers 80%)</option>
                <option value="browser">Window Shoppers (High View, No Buy)</option>
              </select>
            </div>

            <div className="glass-card">
              <h3 className="section-title"><Clock size={18} /> Time-Bound Execution</h3>
              <select value={duration} onChange={e => setDuration(parseInt(e.target.value))} style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: '#f59e0b', marginTop: '1rem' }}>
                <option value={0}>Run Indefinitely (Dangerous)</option>
                <option value={5}>5 Minutes</option>
                <option value={15}>15 Minutes</option>
                <option value={60}>1 Hour</option>
              </select>
              <p style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.5rem' }}>Auto-reverts to Default settings when expired.</p>
            </div>

          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '2rem' }}>
            <button onClick={handleApply} style={{ padding: '1rem 2rem', borderRadius: '8px', background: 'linear-gradient(135deg, #8b5cf6, #3b82f6)', color: 'white', fontWeight: 'bold', border: 'none', cursor: 'pointer', fontSize: '1.1rem', boxShadow: '0 4px 15px rgba(139, 92, 246, 0.4)' }}>
              DEPLOY CONFIGURATION
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
