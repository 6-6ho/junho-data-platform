import { Routes, Route, Navigate, NavLink, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { BarChart3 } from 'lucide-react';
import { fetchSummary } from './api/client';
import OverviewPage from './pages/OverviewPage';
import DQPage from './pages/DQPage';
import MartPage from './pages/MartPage';

function Live() {
  const { data } = useQuery({ queryKey: ['summary-live'], queryFn: fetchSummary, refetchInterval: 30_000 });
  const s = data?.data_freshness_sec ?? null;
  const cls = s === null ? 'dead' : s < 120 ? '' : s < 600 ? 'stale' : 'dead';
  const txt = s === null ? 'NO DATA' : s < 120 ? 'LIVE' : s < 600 ? `${Math.floor(s / 60)}m` : 'STALE';
  return (
    <div className="live" role="status" aria-label={`데이터: ${txt}`}>
      <span className={`live-dot ${cls}`} />
      <span>{txt}</span>
    </div>
  );
}

export default function App() {
  const { pathname } = useLocation();
  const t = pathname.startsWith('/dq') ? 'dq' : pathname.startsWith('/mart') ? 'mart' : 'ov';
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header className="hdr">
        <div className="hdr-l">
          <span className="logo"><BarChart3 size={16} /> shop.analytics</span>
          <nav aria-label="메인">
            <NavLink to="/" className={t === 'ov' ? 'active' : ''}>Overview</NavLink>
            <NavLink to="/dq" className={t === 'dq' ? 'active' : ''}>Data Quality</NavLink>
            <NavLink to="/mart" className={t === 'mart' ? 'active' : ''}>Mart</NavLink>
          </nav>
        </div>
        <Live />
      </header>
      <main className="main" style={{ flex: 1 }}>
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/dq" element={<DQPage />} />
          <Route path="/mart" element={<MartPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
