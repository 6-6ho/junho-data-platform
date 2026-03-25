
import { useState, useEffect } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, ReferenceLine
} from 'recharts'
import {
  Layers, Zap, DollarSign, Clock, Shield,
  LayoutDashboard, Activity, ChevronLeft, ChevronRight, Globe
} from 'lucide-react'

import StatCard from './components/StatCard'

// ==========================================
// Types
// ==========================================
interface SummaryData {
  total_events: number
  today_events: number
  today_revenue: number
  data_freshness_sec: number | null
}

interface HourlyTrafficRow {
  time: string
  [category: string]: string | number
}

interface DQScoreRow {
  date: string
  completeness_score: number
  validity_score: number
  timeliness_score: number
  total_score: number
}

interface DQRuleRow {
  dimension: string
  rule_name: string
  target: string
  layer: string
  trigger_count_7d: number
  status: string
}

interface ReconciliationTrendRow {
  hour: string
  category_total: number
  payment_total: number
  diff_pct: number
}

interface HourlyThroughputRow {
  hour: string
  total_orders: number
}

interface DashboardData {
  summary: SummaryData | null
  hourly_traffic: HourlyTrafficRow[]
  hourly_throughput: HourlyThroughputRow[]
  dq_score_trend: DQScoreRow[]
  dq_rules: DQRuleRow[]
  dq_reconciliation: ReconciliationTrendRow[]
}

const API_BASE = '/api/analytics'

const GRAPH_COLORS = {
  primary: '#3b82f6',
  secondary: '#8b5cf6',
  success: '#10b981',
  warning: '#f59e0b',
  danger: '#ef4444',
  text: '#6b7280',
  active: '#775DD0'
}

const CATEGORY_COLORS: Record<string, string> = {
  Electronics: '#3b82f6',
  Fashion: '#8b5cf6',
  Food: '#10b981',
  Home: '#f59e0b',
  Sports: '#ef4444',
}

// ==========================================
// Components
// ==========================================

const LoadingSpinner = () => (
  <div className="loading">
    <div className="spinner" />
  </div>
)

const formatNumber = (num: number) => {
  if (!num) return '0'
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
  return num.toLocaleString()
}

const formatCurrency = (num: number) => {
  if (!num) return '₩0'
  if (num >= 100000000) return `₩${(num / 100000000).toFixed(1)}억`
  if (num >= 10000) return `₩${(num / 10000).toFixed(0)}만`
  return `₩${num.toLocaleString()}`
}

const formatFreshness = (sec: number | null) => {
  if (sec === null || sec === undefined) return '—'
  if (sec < 60) return `${sec}초 전`
  if (sec < 3600) return `${Math.floor(sec / 60)}분 전`
  if (sec < 86400) return `${Math.floor(sec / 3600)}시간 전`
  return `${Math.floor(sec / 86400)}일 전`
}

const DIMENSION_COLORS: Record<string, string> = {
  'Completeness': 'dim-completeness',
  'Validity': 'dim-validity',
  'Timeliness': 'dim-timeliness',
  'Consistency': 'dim-consistency',
}

// --- Pages ---

const OverviewPage = ({ data }: { data: DashboardData }) => {
  const allCategories = Array.from(
    new Set(data.hourly_traffic.flatMap(row => Object.keys(row).filter(k => k !== 'time')))
  )

  const avgOrders = data.hourly_throughput.length > 0
    ? Math.round(data.hourly_throughput.reduce((sum, r) => sum + r.total_orders, 0) / data.hourly_throughput.length)
    : 0

  return (
    <div className="page-content">
      <div className="bento-grid bento-grid-4">
        <StatCard
          label="총 처리 이벤트"
          value={data.summary ? formatNumber(data.summary.total_events) : '—'}
          icon={Layers}
          iconColor={GRAPH_COLORS.primary}
          trend={{ label: '전체', isPositive: true }}
        />
        <StatCard
          label="오늘 처리량"
          value={data.summary ? formatNumber(data.summary.today_events) : '—'}
          icon={Zap}
          iconColor={GRAPH_COLORS.success}
          trend={{ label: '24시간', isPositive: true }}
        />
        <StatCard
          label="오늘 매출"
          value={data.summary ? formatCurrency(data.summary.today_revenue) : '—'}
          icon={DollarSign}
          iconColor={GRAPH_COLORS.secondary}
          trend={{ label: '24시간', isPositive: true }}
        />
        <StatCard
          label="데이터 신선도"
          value={data.summary ? formatFreshness(data.summary.data_freshness_sec) : '—'}
          icon={Clock}
          iconColor={GRAPH_COLORS.warning}
        />
      </div>

      <div className="chart-grid-2col">
        <div className="glass-card">
          <h3 className="section-title"><Activity size={18} /> 시간대별 카테고리 트래픽</h3>
          <ResponsiveContainer width="100%" height={320}>
            <AreaChart data={data.hourly_traffic}>
              <defs>
                {allCategories.map(cat => (
                  <linearGradient key={cat} id={`color-${cat}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={CATEGORY_COLORS[cat] || '#6b7280'} stopOpacity={0.4} />
                    <stop offset="95%" stopColor={CATEGORY_COLORS[cat] || '#6b7280'} stopOpacity={0} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis
                dataKey="time"
                stroke="#64748b"
                tick={{ fill: '#64748b', fontSize: 10, fontFamily: 'var(--font-main)' }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(t) => {
                  try { return new Date(t).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }) }
                  catch { return t }
                }}
              />
              <YAxis stroke="#64748b" tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                itemStyle={{ color: '#fff', fontSize: '12px' }}
                labelFormatter={(t) => {
                  try { return new Date(t).toLocaleString('ko-KR') }
                  catch { return t }
                }}
              />
              {allCategories.map(cat => (
                <Area
                  key={cat}
                  type="monotone"
                  dataKey={cat}
                  stackId="1"
                  stroke={CATEGORY_COLORS[cat] || '#6b7280'}
                  strokeWidth={2}
                  fill={`url(#color-${cat})`}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="glass-card">
          <h3 className="section-title"><Zap size={18} /> 시간별 처리량 추이</h3>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={data.hourly_throughput} margin={{ top: 10, right: 30, left: 0, bottom: 5 }}>
              <defs>
                <linearGradient id="throughputGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={GRAPH_COLORS.primary} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={GRAPH_COLORS.primary} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis
                dataKey="hour"
                stroke="#64748b"
                tick={{ fill: '#64748b', fontSize: 10, fontFamily: 'var(--font-main)' }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(h) => {
                  try { return new Date(h).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }) }
                  catch { return h }
                }}
              />
              <YAxis stroke="#64748b" tick={{ fill: '#64748b', fontSize: 11 }} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                itemStyle={{ color: '#fff', fontSize: '12px' }}
                formatter={(value: number | undefined) => [(value ?? 0).toLocaleString(), '주문 건수']}
                labelFormatter={(h) => {
                  try { return new Date(h).toLocaleString('ko-KR') }
                  catch { return h }
                }}
              />
              {avgOrders > 0 && (
                <ReferenceLine y={avgOrders} stroke={GRAPH_COLORS.warning} strokeDasharray="5 5" label={{ value: `평균 ${avgOrders}`, fill: GRAPH_COLORS.warning, fontSize: 11 }} />
              )}
              <Line type="monotone" dataKey="total_orders" stroke={GRAPH_COLORS.primary} strokeWidth={2} name="주문 건수" dot={{ r: 3, fill: GRAPH_COLORS.primary }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

const DQPage = ({ data }: { data: DashboardData }) => {
  return (
    <div className="page-content">
      {/* Section 1: DQ Score Trend */}
      <div className="glass-card full-width" style={{ marginBottom: '1.5rem' }}>
        <h3 className="section-title"><Shield size={18} /> DQ 종합 스코어 트렌드 (14일)</h3>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data.dq_score_trend} margin={{ top: 10, right: 30, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="date"
              stroke="#64748b"
              tick={{ fill: '#64748b', fontSize: 11 }}
              tickFormatter={(d) => {
                try { return new Date(d).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' }) }
                catch { return d }
              }}
            />
            <YAxis domain={[0, 100]} stroke="#64748b" tick={{ fill: '#64748b', fontSize: 11 }} />
            <Tooltip
              contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
              itemStyle={{ fontSize: '12px' }}
            />
            <ReferenceLine y={90} stroke="#ef4444" strokeDasharray="5 5" label={{ value: '임계치 90', fill: '#ef4444', fontSize: 11 }} />
            <Line type="monotone" dataKey="completeness_score" stroke={GRAPH_COLORS.primary} strokeWidth={2} name="완전성" dot={false} />
            <Line type="monotone" dataKey="validity_score" stroke={GRAPH_COLORS.success} strokeWidth={2} name="유효성" dot={false} />
            <Line type="monotone" dataKey="timeliness_score" stroke={GRAPH_COLORS.warning} strokeWidth={2} name="적시성" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Section 2: DQ Rules Summary */}
      <div className="glass-card full-width" style={{ marginBottom: '1.5rem' }}>
        <h3 className="section-title"><Shield size={18} /> DQ 규칙 현황</h3>
        <div className="table-container">
          <table className="dq-table">
            <thead>
              <tr>
                <th>Dimension</th>
                <th>규칙명</th>
                <th>대상</th>
                <th>Layer</th>
                <th className="text-right">7일 발동</th>
                <th>상태</th>
              </tr>
            </thead>
            <tbody>
              {data.dq_rules.length > 0 ? data.dq_rules.map((rule, idx) => (
                <tr key={idx}>
                  <td><span className={`badge ${DIMENSION_COLORS[rule.dimension] || ''}`}>{rule.dimension}</span></td>
                  <td>{rule.rule_name}</td>
                  <td className="mono-text">{rule.target}</td>
                  <td><span className={`badge ${rule.layer === 'Stream' ? 'layer-stream' : 'layer-etl'}`}>{rule.layer}</span></td>
                  <td className="text-right">{rule.trigger_count_7d}</td>
                  <td><span className="badge green">active</span></td>
                </tr>
              )) : (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
                    규칙 데이터 로딩 중...
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Section 3: Reconciliation Trend */}
      <div className="glass-card full-width">
        <h3 className="section-title"><Shield size={18} /> 교차 검증 불일치율 추이 (24h)</h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginBottom: '1rem' }}>
          카테고리별 집계 vs 결제수단별 집계 — 같은 이벤트, 다른 차원, 총합 일치 검증
        </p>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data.dq_reconciliation} margin={{ top: 10, right: 30, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="hour"
              stroke="#64748b"
              tick={{ fill: '#64748b', fontSize: 11 }}
              tickFormatter={(h) => {
                try { return new Date(h).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }) }
                catch { return h }
              }}
            />
            <YAxis
              stroke="#64748b"
              tick={{ fill: '#64748b', fontSize: 11 }}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
              itemStyle={{ fontSize: '12px' }}
              formatter={(value: number | undefined) => [`${(value ?? 0).toFixed(1)}%`, '불일치율']}
              labelFormatter={(h) => {
                try { return new Date(h).toLocaleString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit' }) }
                catch { return h }
              }}
            />
            <ReferenceLine y={5} stroke="#ef4444" strokeDasharray="5 5" label={{ value: '임계치 5%', fill: '#ef4444', fontSize: 11 }} />
            <Line type="monotone" dataKey="diff_pct" stroke={GRAPH_COLORS.secondary} strokeWidth={2} name="불일치율" dot={{ r: 3, fill: GRAPH_COLORS.secondary }} />
          </LineChart>
        </ResponsiveContainer>
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
  const [activeTab, setActiveTab] = useState('overview')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [data, setData] = useState<DashboardData>({
    summary: null,
    hourly_traffic: [],
    hourly_throughput: [],
    dq_score_trend: [],
    dq_rules: [],
    dq_reconciliation: []
  })
  const [loading, setLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())

  const fetchData = async () => {
    try {
      const [summaryRes, hourlyRes, throughputRes, scoreTrendRes, rulesRes, reconRes] = await Promise.all([
        fetch(`${API_BASE}/summary`),
        fetch(`${API_BASE}/hourly-traffic`),
        fetch(`${API_BASE}/hourly-throughput`),
        fetch(`${API_BASE}/dq/score-trend`),
        fetch(`${API_BASE}/dq/rules-summary`),
        fetch(`${API_BASE}/dq/reconciliation`)
      ])

      const summary = summaryRes.ok ? await summaryRes.json() : null
      const hourly_traffic = hourlyRes.ok ? await hourlyRes.json() : []
      const hourly_throughput = throughputRes.ok ? await throughputRes.json() : []
      const dq_score_trend = scoreTrendRes.ok ? await scoreTrendRes.json() : []
      const dq_rules = rulesRes.ok ? await rulesRes.json() : []
      const dq_reconciliation = reconRes.ok ? await reconRes.json() : []

      setData({ summary, hourly_traffic, hourly_throughput, dq_score_trend, dq_rules, dq_reconciliation })
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
      <nav className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <Globe size={24} color={GRAPH_COLORS.active} />
            <h1>Shop<span style={{ color: GRAPH_COLORS.active }}>Analytics</span></h1>
          </div>
          <ToggleButton collapsed={sidebarCollapsed} onClick={() => setSidebarCollapsed(!sidebarCollapsed)} />
        </div>

        <div className="nav-links">
          <button
            className={`nav-item ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
            title="파이프라인 Overview"
          >
            <LayoutDashboard size={20} />
            <span>파이프라인 Overview</span>
          </button>

          <button
            className={`nav-item ${activeTab === 'dq' ? 'active' : ''}`}
            onClick={() => setActiveTab('dq')}
            title="데이터 품질 (DQ)"
          >
            <Shield size={20} />
            <span>데이터 품질 (DQ)</span>
          </button>
        </div>

        <div className="sidebar-footer">
          <div className="live-status" title={`최근 업데이트: ${lastUpdate.toLocaleTimeString()}\n상태: 정상 가동 중`}>
            <div className="live-dot" />
            <span>{loading ? 'Syncing...' : 'System Normal'}</span>
          </div>
        </div>
      </nav>

      <main className="main-content">
        {activeTab === 'overview' && <OverviewPage data={data} />}
        {activeTab === 'dq' && <DQPage data={data} />}
      </main>
    </div>
  )
}

export default App
