
// Force Update: v2
import { useState, useEffect } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell
} from 'recharts'
import {
  Activity, TrendingUp, Users, ShoppingCart, Layers, Zap, Globe,
  LayoutDashboard, GitMerge, Award, ChevronLeft, ChevronRight
} from 'lucide-react'


import StatCard from './components/StatCard'

// ==========================================
// Types
// ==========================================
interface AffinityRule {
  antecedents: string;
  consequents: string;
  confidence: number;
  lift: number;
  support: number;
}

interface RFMSegment {
  segment: string;
  count: number;
  percentage: number;
}

interface SummaryData {
  total_events: number
  today_records: number
  conversion_rate: number
  top_brands: string[]
}

interface HourlyData {
  hour: number
  count: number
}

interface BrandData {
  brand: string
  count: number
  percentage: number
}

interface FunnelData {
  page_view: number
  add_to_cart: number
  purchase: number
  conversion_rate: number
}

interface DashboardData {
  summary: SummaryData | null
  hourly_traffic: HourlyData[]
  brand_stats: BrandData[]
  funnel: FunnelData | null
  affinity: { rules: AffinityRule[], count: number } | null
  rfm: RFMSegment[]
}

const API_BASE = '/api/analytics'

const GRAPH_COLORS = {
  primary: '#3b82f6',   // Blue
  secondary: '#8b5cf6', // Purple
  success: '#10b981',   // Green
  warning: '#f59e0b',   // Orange
  danger: '#ef4444',    // Red
  grid: 'rgba(255, 255, 255, 0.05)',
  text: '#6b7280',
  white: '#ffffff',
  active: '#775DD0' // Shop Purple
}

// ==========================================
// Components
// ==========================================



const LoadingSpinner = () => (
  <div className="loading">
    <div className="spinner" />
  </div>
);

// --- Pages ---

const DashboardPage = ({ data }: { data: DashboardData }) => {
  const formatNumber = (num: number) => {
    if (!num) return '0'
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
    return num.toLocaleString()
  }

  return (
    <div className="page-content">
      {/* Bento Grid Stats */}
      {/* Bento Grid Stats */}
      <div className="bento-grid">
        <StatCard
          label="총 발생 이벤트"
          value={data.summary ? formatNumber(data.summary.total_events) : '—'}
          icon={Layers}
          iconColor={GRAPH_COLORS.primary}
          trend={{ label: '실시간', isPositive: true }}
          tooltip="전체 처리된 이벤트 수"
        />
        <StatCard
          label="금일 데이터 통계"
          value={data.summary ? formatNumber(data.summary.today_records) : '—'}
          icon={Zap}
          iconColor={GRAPH_COLORS.success}
          trend={{ label: '24시간', isPositive: true }}
          tooltip="최근 24시간 내 수집"
        />
        <StatCard
          label="구매 전환율"
          value={data.summary ? `${data.summary.conversion_rate.toFixed(1)}%` : '—'}
          icon={ShoppingCart}
          iconColor={GRAPH_COLORS.secondary}
        />
        <StatCard
          label="인기 브랜드"
          value={data.summary?.top_brands?.[0] || '—'}
          icon={Activity}
          iconColor={GRAPH_COLORS.warning}
        />
      </div>

      <div className="chart-section">
        <div className="glass-card">
          <h3 className="section-title"><TrendingUp size={18} /> 시간대별 트래픽 추이</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={data.hourly_traffic}>
              <defs>
                <linearGradient id="colorTraffic" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={GRAPH_COLORS.primary} stopOpacity={0.4} />
                  <stop offset="95%" stopColor={GRAPH_COLORS.primary} stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorVip" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={GRAPH_COLORS.warning} stopOpacity={0.8} />
                  <stop offset="95%" stopColor={GRAPH_COLORS.warning} stopOpacity={0.3} />
                </linearGradient>
                <linearGradient id="colorLoyal" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={GRAPH_COLORS.secondary} stopOpacity={0.8} />
                  <stop offset="95%" stopColor={GRAPH_COLORS.secondary} stopOpacity={0.3} />
                </linearGradient>
                <linearGradient id="colorRisk" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={GRAPH_COLORS.danger} stopOpacity={0.8} />
                  <stop offset="95%" stopColor={GRAPH_COLORS.danger} stopOpacity={0.3} />
                </linearGradient>
                <linearGradient id="colorPrimary" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={GRAPH_COLORS.primary} stopOpacity={0.8} />
                  <stop offset="95%" stopColor={GRAPH_COLORS.primary} stopOpacity={0.3} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis
                dataKey="hour"
                stroke="#64748b"
                tick={{ fill: '#64748b', fontSize: 11, fontFamily: 'var(--font-main)' }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(h) => `${h}시`}
              />
              <YAxis
                stroke="#64748b"
                tick={{ fill: '#64748b', fontSize: 11, fontFamily: 'var(--font-main)' }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)' }}
                itemStyle={{ color: '#fff', fontSize: '12px', fontFamily: 'var(--font-main)' }}
                cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 2, strokeDasharray: '4 4' }}
              />
              <Area
                type="monotone"
                dataKey="count"
                stroke={GRAPH_COLORS.primary}
                strokeWidth={3}
                fill="url(#colorTraffic)"
                animationDuration={2000}
                animationEasing="ease-out"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="glass-card">
          <h3 className="section-title"><Globe size={18} /> 브랜드 점유율</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data.brand_stats.slice(0, 5)} layout="vertical" margin={{ left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke="rgba(255,255,255,0.05)" />
              <XAxis type="number" hide />
              <YAxis
                dataKey="brand"
                type="category"
                width={110}
                stroke="#94a3b8"
                tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'var(--font-main)' }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff', fontFamily: 'var(--font-main)' }}
              />
              <Bar dataKey="count" fill={GRAPH_COLORS.secondary} barSize={20} radius={[0, 4, 4, 0]} animationDuration={1500}>
                {data.brand_stats.slice(0, 5).map((_entry, index) => (
                  <Cell key={`cell-${index}`} fill={index < 3 ? GRAPH_COLORS.active : GRAPH_COLORS.secondary} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

const AffinityPage = ({ data }: { data: DashboardData }) => {
  return (
    <div className="page-content">
      <div className="page-header">
        <h2>장바구니 연관 분석</h2>
        <p>Spark FP-Growth 기반 머신러닝 분석</p>
      </div>

      <div className="glass-card full-width">
        <h3 className="section-title"><GitMerge size={18} /> 연관 규칙 리스트</h3>
        <div className="table-container">
          <table className="brand-table">
            <thead>
              <tr>
                <th>기준 상품 (Reference)</th>
                <th>연관 구매 상품 (Recommendation)</th>
                <th className="text-right">신뢰도</th>
                <th className="text-right">향상도</th>
                <th className="text-right">지지도</th>
              </tr>
            </thead>
            <tbody>
              {data.affinity?.rules && data.affinity.rules.length > 0 ? (
                data.affinity.rules.map((rule, idx) => (
                  <tr key={idx}>
                    <td className="mono-text">{rule.antecedents.replace(/[\[\]"]/g, '')}</td>
                    <td className="mono-text highlight">{rule.consequents.replace(/[\[\]"]/g, '')}</td>
                    <td className="text-right"><div className="badge blue">{(rule.confidence * 100).toFixed(1)}%</div></td>
                    <td className="text-right"><div className="badge purple">{rule.lift.toFixed(2)}x</div></td>
                    <td className="text-right">{rule.support.toFixed(4)}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
                    연관 규칙 분석을 위한 충분한 데이터가 수집되지 않았습니다.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

const RFMPage = ({ data }: { data: DashboardData }) => {
  return (
    <div className="page-content">
      <div className="page-header">
        <h2>고객 세그먼트 (RFM)</h2>
        <p>최근성(Recency), 빈도(Frequency), 금액(Monetary) 분석</p>
      </div>

      <div className="chart-section single">
        <div className="glass-card">
          <h3 className="section-title"><Users size={18} /> 등급별 고객 분포</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data.rfm} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <defs>
                <linearGradient id="colorVip" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={GRAPH_COLORS.warning} stopOpacity={1} />
                  <stop offset="95%" stopColor={GRAPH_COLORS.warning} stopOpacity={0.6} />
                </linearGradient>
                <linearGradient id="colorLoyal" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={GRAPH_COLORS.secondary} stopOpacity={1} />
                  <stop offset="95%" stopColor={GRAPH_COLORS.secondary} stopOpacity={0.6} />
                </linearGradient>
                <linearGradient id="colorRisk" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={GRAPH_COLORS.danger} stopOpacity={1} />
                  <stop offset="95%" stopColor={GRAPH_COLORS.danger} stopOpacity={0.6} />
                </linearGradient>
                <linearGradient id="colorPrimary" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={GRAPH_COLORS.primary} stopOpacity={1} />
                  <stop offset="95%" stopColor={GRAPH_COLORS.primary} stopOpacity={0.6} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={GRAPH_COLORS.grid} vertical={false} />
              <XAxis dataKey="segment" stroke={GRAPH_COLORS.text} fontSize={12} fontFamily="var(--font-main)" />
              <YAxis stroke={GRAPH_COLORS.text} fontSize={12} fontFamily="var(--font-main)" />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: 'none', fontFamily: 'var(--font-main)' }}
                cursor={{ fill: 'rgba(255,255,255,0.05)' }}
              />
              <Bar dataKey="count" fill={GRAPH_COLORS.primary} radius={[4, 4, 0, 0]} animationDuration={1500} animationEasing="ease-out">
                {data.rfm.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={
                    entry.segment === 'VIP' ? 'url(#colorVip)' :
                      entry.segment === 'Loyal' ? 'url(#colorLoyal)' :
                        entry.segment === 'Risk' ? 'url(#colorRisk)' :
                          'url(#colorPrimary)'
                  } />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="glass-card full-width">
        <h3 className="section-title"><Award size={18} /> 등급 상세 현황</h3>
        <table className="brand-table">
          <thead>
            <tr>
              <th>등급명</th>
              <th>고객 수</th>
              <th>비율</th>
            </tr>
          </thead>
          <tbody>
            {data.rfm.map((seg, idx) => (
              <tr key={idx}>
                <td><span className={`status-dot ${seg.segment.toLowerCase()}`}></span>{seg.segment}</td>
                <td>{seg.count.toLocaleString()}명</td>
                <td>{seg.percentage}%</td>
              </tr>
            ))}
            {data.rfm.length === 0 && (
              <tr>
                <td colSpan={3} style={{ textAlign: 'center', padding: '2rem' }}>RFM 데이터가 없습니다.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

const ToggleButton = ({ collapsed, onClick }: { collapsed: boolean; onClick: () => void }) => (
  <button className="sidebar-toggle-btn" onClick={onClick}>
    {collapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
  </button>
)

// ==========================================
// Main App Shell
// ==========================================

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [data, setData] = useState<DashboardData>({
    summary: null,
    hourly_traffic: [],
    brand_stats: [],
    funnel: null,
    affinity: null,
    rfm: []
  })
  const [loading, setLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())

  const fetchData = async () => {
    try {
      const [summaryRes, hourlyRes, brandRes, funnelRes, affinityRes, rfmRes] = await Promise.all([
        fetch(`${API_BASE}/summary`),
        fetch(`${API_BASE}/hourly-traffic`),
        fetch(`${API_BASE}/brand-distribution`),
        fetch(`${API_BASE}/funnel`),
        fetch(`${API_BASE}/affinity?limit=10`),
        fetch(`${API_BASE}/rfm`)
      ])

      const summary = summaryRes.ok ? await summaryRes.json() : null;
      const hourly_traffic = hourlyRes.ok ? await hourlyRes.json() : [];
      const brand_stats = brandRes.ok ? await brandRes.json() : [];
      const funnel = funnelRes.ok ? await funnelRes.json() : null;
      const affinity = affinityRes.ok ? await affinityRes.json() : null;
      const rfm = rfmRes.ok ? await rfmRes.json() : [];

      setData({ summary, hourly_traffic, brand_stats, funnel, affinity, rfm })
      setLastUpdate(new Date())
    } catch (error) {
      console.error('Failed to fetch data', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])

  if (loading) return <LoadingSpinner />

  return (
    <div className="app-container">
      {/* Sidebar */}
      {/* Sidebar */}
      <nav className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <Globe size={24} color={GRAPH_COLORS.secondary} />
            <h1>Shop<span style={{ color: GRAPH_COLORS.secondary }}>Analytics</span></h1>
          </div>
          <ToggleButton collapsed={sidebarCollapsed} onClick={() => setSidebarCollapsed(!sidebarCollapsed)} />
        </div>

        <div className="nav-links">
          <button
            className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
            title="통합 대시보드"
          >
            <LayoutDashboard size={20} />
            <span>통합 대시보드</span>
          </button>

          <div className="nav-group-label">분석 인사이트 (Insights)</div>

          <button
            className={`nav-item ${activeTab === 'affinity' ? 'active' : ''}`}
            onClick={() => setActiveTab('affinity')}
            title="장바구니 연관 분석"
          >
            <GitMerge size={20} />
            <span>장바구니 연관 분석</span>
          </button>

          <button
            className={`nav-item ${activeTab === 'rfm' ? 'active' : ''}`}
            onClick={() => setActiveTab('rfm')}
            title="고객 등급(RFM) 분석"
          >
            <Users size={20} />
            <span>고객 등급(RFM) 분석</span>
          </button>
        </div>

        <div className="sidebar-footer">
          <div className="live-status" title={`최근 업데이트: ${lastUpdate.toLocaleTimeString()}\n상태: 정상 가동 중`}>
            <div className="live-dot" />
            <span>{loading ? 'Syncing...' : 'System Normal'}</span>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="main-content">
        {activeTab === 'dashboard' && <DashboardPage data={data} />}
        {activeTab === 'affinity' && <AffinityPage data={data} />}
        {activeTab === 'rfm' && <RFMPage data={data} />}
      </main>
    </div>
  )
}

export default App
