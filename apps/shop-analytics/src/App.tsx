import { Routes, Route, Navigate, NavLink, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { BarChart3 } from 'lucide-react';
import { fetchSummary } from './api/client';
import OverviewPage from './pages/OverviewPage';
import DQPage from './pages/DQPage';
import MartPage from './pages/MartPage';

function LiveDot() {
  const { data: summary } = useQuery({
    queryKey: ['summary-live'],
    queryFn: fetchSummary,
    refetchInterval: 30_000,
  });

  const sec = summary?.data_freshness_sec ?? null;
  const cls =
    sec === null ? 'dead' : sec < 120 ? '' : sec < 600 ? 'stale' : 'dead';
  const label =
    sec === null
      ? 'No data'
      : sec < 120
        ? 'Live'
        : sec < 600
          ? `${Math.floor(sec / 60)}m ago`
          : 'Stale';

  return (
    <div className="live-indicator">
      <div className={`live-dot ${cls}`} />
      <span>{label}</span>
    </div>
  );
}

export default function App() {
  const { pathname } = useLocation();
  const tab = pathname.startsWith('/dq')
    ? 'dq'
    : pathname.startsWith('/mart')
      ? 'mart'
      : 'overview';

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header className="header">
        <div className="header-left">
          <span className="logo">
            <BarChart3 size={20} className="logo-icon" />
            Shop Analytics
          </span>
          <nav>
            <NavLink to="/" className={tab === 'overview' ? 'active' : ''}>
              Overview
            </NavLink>
            <NavLink to="/dq" className={tab === 'dq' ? 'active' : ''}>
              Data Quality
            </NavLink>
            <NavLink to="/mart" className={tab === 'mart' ? 'active' : ''}>
              Mart
            </NavLink>
          </nav>
        </div>
        <LiveDot />
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
