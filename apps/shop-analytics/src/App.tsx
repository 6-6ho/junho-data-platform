import { useState, useEffect } from 'react'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts'
import {
  Activity, TrendingUp, Users, ShoppingCart,
  ArrowUpRight, ArrowDownRight, Database, Clock, RefreshCw
} from 'lucide-react'
import './App.css'

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

const API_BASE = '/api/analytics'

const COLORS = ['#3b82f6', '#8b5cf6', '#0ecb81', '#f6465d', '#eab839']

function App() {
  const [summary, setSummary] = useState<SummaryData | null>(null)
  const [hourlyData, setHourlyData] = useState<HourlyData[]>([])
  const [brandData, setBrandData] = useState<BrandData[]>([])
  const [funnelData, setFunnelData] = useState<FunnelData | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())

  const fetchData = async () => {
    try {
      const [summaryRes, hourlyRes, brandRes, funnelRes] = await Promise.all([
        fetch(`${API_BASE}/summary`),
        fetch(`${API_BASE}/hourly-traffic`),
        fetch(`${API_BASE}/brand-distribution`),
        fetch(`${API_BASE}/funnel`)
      ])

      if (summaryRes.ok) setSummary(await summaryRes.json())
      if (hourlyRes.ok) setHourlyData(await hourlyRes.json())
      if (brandRes.ok) setBrandData(await brandRes.json())
      if (funnelRes.ok) setFunnelData(await funnelRes.json())

      setLastUpdate(new Date())
    } catch (error) {
      console.error('Failed to fetch analytics data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [])

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
    return num.toString()
  }

  if (loading) {
    return (
      <div className="dashboard">
        <div className="loading">
          <RefreshCw className="spinner" size={24} />
          Loading analytics...
        </div>
      </div>
    )
  }

  return (
    <div className="dashboard">
      <div className="header">
        <h1>Shop Analytics Dashboard</h1>
        <p>
          <Clock size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} />
          Last updated: {lastUpdate.toLocaleTimeString()}
        </p>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="label">
            <Database size={16} />
            Total Events
          </div>
          <div className="value blue">
            {summary ? formatNumber(summary.total_events) : '—'}
          </div>
          <div className="change positive">
            <ArrowUpRight size={14} />
            +12.5% from yesterday
          </div>
        </div>

        <div className="stat-card">
          <div className="label">
            <Activity size={16} />
            Today's Records
          </div>
          <div className="value green">
            {summary ? formatNumber(summary.today_records) : '—'}
          </div>
          <div className="change positive">
            <ArrowUpRight size={14} />
            +8.2% from avg
          </div>
        </div>

        <div className="stat-card">
          <div className="label">
            <ShoppingCart size={16} />
            Conversion Rate
          </div>
          <div className="value purple">
            {summary ? `${summary.conversion_rate.toFixed(1)}%` : '—'}
          </div>
          <div className="change negative">
            <ArrowDownRight size={14} />
            -0.3% from last week
          </div>
        </div>

        <div className="stat-card">
          <div className="label">
            <Users size={16} />
            Top Brand
          </div>
          <div className="value" style={{ fontSize: '20px' }}>
            {summary?.top_brands?.[0] || '—'}
          </div>
          <div className="change positive">
            <TrendingUp size={14} />
            Highest activity
          </div>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="charts-grid">
        <div className="chart-card">
          <h3>
            <Activity className="icon" size={18} />
            Hourly Traffic (24h)
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={hourlyData}>
              <defs>
                <linearGradient id="colorTraffic" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#2b3139" />
              <XAxis
                dataKey="hour"
                stroke="#848e9c"
                fontSize={12}
                tickFormatter={(h) => `${h}:00`}
              />
              <YAxis stroke="#848e9c" fontSize={12} />
              <Tooltip
                contentStyle={{
                  background: '#1e2329',
                  border: '1px solid #2b3139',
                  borderRadius: 8
                }}
              />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#3b82f6"
                fillOpacity={1}
                fill="url(#colorTraffic)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>
            <TrendingUp className="icon" size={18} />
            Brand Distribution
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={brandData.slice(0, 6)} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#2b3139" />
              <XAxis type="number" stroke="#848e9c" fontSize={12} />
              <YAxis
                dataKey="brand"
                type="category"
                stroke="#848e9c"
                fontSize={12}
                width={80}
              />
              <Tooltip
                contentStyle={{
                  background: '#1e2329',
                  border: '1px solid #2b3139',
                  borderRadius: 8
                }}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {brandData.slice(0, 6).map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Funnel Chart */}
      <div className="chart-card" style={{ marginBottom: 24 }}>
        <h3>
          <ShoppingCart className="icon" size={18} />
          Conversion Funnel
        </h3>
        {funnelData && (
          <div className="funnel-container">
            <div className="funnel-step">
              <span className="funnel-label">Page Views</span>
              <div className="funnel-bar" style={{ width: '100%' }}>
                {formatNumber(funnelData.page_view)}
              </div>
              <span className="funnel-value">100%</span>
            </div>
            <div className="funnel-step">
              <span className="funnel-label">Add to Cart</span>
              <div
                className="funnel-bar"
                style={{
                  width: `${(funnelData.add_to_cart / funnelData.page_view * 100)}%`,
                  background: 'linear-gradient(90deg, #8b5cf6, #a78bfa)'
                }}
              >
                {formatNumber(funnelData.add_to_cart)}
              </div>
              <span className="funnel-value">
                {(funnelData.add_to_cart / funnelData.page_view * 100).toFixed(1)}%
              </span>
            </div>
            <div className="funnel-step">
              <span className="funnel-label">Purchase</span>
              <div
                className="funnel-bar"
                style={{
                  width: `${(funnelData.purchase / funnelData.page_view * 100)}%`,
                  background: 'linear-gradient(90deg, #0ecb81, #34d399)'
                }}
              >
                {formatNumber(funnelData.purchase)}
              </div>
              <span className="funnel-value">
                {funnelData.conversion_rate.toFixed(1)}%
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Top Brands Table */}
      <div className="table-card">
        <h3>Brand Performance</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Brand</th>
              <th>Events</th>
              <th>Share</th>
            </tr>
          </thead>
          <tbody>
            {brandData.slice(0, 10).map((brand, idx) => (
              <tr key={brand.brand}>
                <td>#{idx + 1}</td>
                <td>{brand.brand}</td>
                <td>{formatNumber(brand.count)}</td>
                <td>{brand.percentage.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default App
