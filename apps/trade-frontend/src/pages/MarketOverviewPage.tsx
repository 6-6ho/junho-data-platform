import { useQuery } from '@tanstack/react-query';
import {
  fetchRecentListings,
  fetchListingStats,
  fetchWhaleDashboard,
  fetchWhaleActiveEpisodes,
  fetchWhaleEpisodes,
  fetchWhaleStats,
} from '../api/client';

function timeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffSec = Math.floor((now - then) / 1000);

  if (diffSec < 60) return '방금';
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}분 전`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}시간 전`;
  if (diffSec < 172800) return '어제';
  return `${Math.floor(diffSec / 86400)}일 전`;
}

function formatUsd(v: number | null): string {
  if (v == null) return '-';
  if (Math.abs(v) >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (Math.abs(v) >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
  return `$${v.toFixed(0)}`;
}

function pctColor(v: number | null): string {
  if (v == null) return 'var(--text-tertiary)';
  if (v > 0) return 'var(--green)';
  if (v < 0) return 'var(--red)';
  return 'var(--text-secondary)';
}

function formatPct(v: number | null): string {
  if (v == null) return '-';
  return `${v > 0 ? '+' : ''}${v.toFixed(1)}%`;
}

const LABEL_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
  squeeze_reversal: { icon: '\u26A1', color: '#f59e0b', label: 'Squeeze Reversal' },
  squeeze_continuation: { icon: '\u{1F504}', color: '#3b82f6', label: 'Squeeze Continuation' },
  genuine_rally: { icon: '\u2705', color: '#10b981', label: 'Genuine Rally' },
  genuine_sustained: { icon: '\u{1F680}', color: '#8b5cf6', label: 'Genuine Sustained' },
  fakeout: { icon: '\u{1F4A8}', color: '#ef4444', label: 'Fakeout' },
};

function MarketOverviewPage() {
  // Listing queries
  const { data: stats } = useQuery({
    queryKey: ['listing-stats'],
    queryFn: fetchListingStats,
    refetchInterval: 60_000,
  });
  const { data: recent } = useQuery({
    queryKey: ['listing-recent'],
    queryFn: () => fetchRecentListings({ limit: 30 }),
    refetchInterval: 60_000,
  });

  // Whale queries
  const { data: dashboard } = useQuery({
    queryKey: ['whale-dashboard'],
    queryFn: fetchWhaleDashboard,
    refetchInterval: 10_000,
  });
  const { data: activeEps } = useQuery({
    queryKey: ['whale-active-episodes'],
    queryFn: fetchWhaleActiveEpisodes,
    refetchInterval: 15_000,
  });
  const { data: recentEps } = useQuery({
    queryKey: ['whale-recent-episodes'],
    queryFn: () => fetchWhaleEpisodes({ limit: 10 }),
    refetchInterval: 30_000,
  });
  const { data: whaleStats } = useQuery({
    queryKey: ['whale-stats'],
    queryFn: fetchWhaleStats,
    refetchInterval: 60_000,
  });

  const events = recent?.events ?? [];
  const depth = dashboard?.depth;
  const liqs = dashboard?.liquidations_5m;
  const whaleTrades = dashboard?.recent_whale_trades ?? [];
  const activeEpisodes = activeEps?.episodes ?? [];
  const recentEpisodes = recentEps?.episodes ?? [];
  const labelDist = whaleStats?.label_distribution ?? [];

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      {/* === BTC 현재 상태 === */}
      <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
        <div className="card-body" style={{ padding: 'var(--space-6)' }}>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-3)', fontWeight: 'var(--font-semibold)' }}>
            BTC 현재 상태
          </div>
          {depth ? (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-6)' }}>
              <div>
                <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 'var(--font-bold)', color: 'var(--text-primary)' }}>
                  ${depth.mid_price?.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>Mid Price</div>
              </div>
              <div>
                <div style={{ fontSize: 'var(--text-lg)', fontWeight: 'var(--font-bold)', color: pctColor(depth.depth_imbalance ? depth.depth_imbalance * 100 : null) }}>
                  {depth.depth_imbalance != null ? `${(depth.depth_imbalance * 100).toFixed(0)}%` : '-'}
                </div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
                  호가 불균형 {depth.depth_imbalance != null && depth.depth_imbalance > 0 ? '(매수 우세)' : depth.depth_imbalance != null && depth.depth_imbalance < 0 ? '(매도 우세)' : ''}
                </div>
              </div>
              <div>
                <div style={{ fontSize: 'var(--text-lg)', fontWeight: 'var(--font-semibold)', color: 'var(--text-primary)' }}>
                  {formatUsd(depth.bid_depth_1pct)} / {formatUsd(depth.ask_depth_1pct)}
                </div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>매수벽 / 매도벽 (1%)</div>
              </div>
            </div>
          ) : (
            <div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-sm)' }}>데이터 수집 중...</div>
          )}

          {/* 5분 청산 요약 */}
          {liqs && (liqs.short_liq_count > 0 || liqs.long_liq_count > 0) && (
            <div style={{ display: 'flex', gap: 'var(--space-6)', marginTop: 'var(--space-4)', paddingTop: 'var(--space-4)', borderTop: '1px solid var(--border)' }}>
              <div>
                <span style={{ color: 'var(--red)', fontWeight: 'var(--font-semibold)' }}>
                  {liqs.short_liq_count}건 / {formatUsd(liqs.short_liq_usd)}
                </span>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>숏 청산 (5분)</div>
              </div>
              <div>
                <span style={{ color: 'var(--green)', fontWeight: 'var(--font-semibold)' }}>
                  {liqs.long_liq_count}건 / {formatUsd(liqs.long_liq_usd)}
                </span>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>롱 청산 (5분)</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* === 진행 중인 에피소드 === */}
      {activeEpisodes.length > 0 && (
        <div className="card" style={{ marginBottom: 'var(--space-4)', border: '1px solid var(--yellow, #f59e0b)' }}>
          <div className="card-body" style={{ padding: 'var(--space-6)' }}>
            <div style={{ fontSize: 'var(--text-sm)', color: '#f59e0b', marginBottom: 'var(--space-4)', fontWeight: 'var(--font-semibold)' }}>
              진행 중인 에피소드 ({activeEpisodes.length})
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              {activeEpisodes.map((ep: any) => (
                <div key={ep.id} style={{ padding: 'var(--space-3) var(--space-4)', borderRadius: 'var(--radius-md)', background: 'var(--bg-secondary)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-2)' }}>
                    <span style={{ fontWeight: 'var(--font-bold)', color: pctColor(ep.price_change_pct) }}>
                      {formatPct(ep.price_change_pct)}
                    </span>
                    <span style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
                      @ ${ep.trigger_price?.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </span>
                    <span style={{ marginLeft: 'auto', color: 'var(--text-tertiary)', fontSize: 'var(--text-xs)' }}>
                      {ep.detected_at ? timeAgo(ep.detected_at) : ''}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 'var(--space-4)', fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
                    {ep.oi_change_pct != null && <span>OI {formatPct(ep.oi_change_pct)}</span>}
                    {ep.short_liq_count > 0 && <span>숏청산 {ep.short_liq_count}건</span>}
                    {ep.long_liq_count > 0 && <span>롱청산 {ep.long_liq_count}건</span>}
                    {ep.whale_net_buy_usd != null && <span>고래 {formatUsd(ep.whale_net_buy_usd)}</span>}
                  </div>
                  {/* 아웃컴 진행 상태 */}
                  <div style={{ display: 'flex', gap: 'var(--space-3)', marginTop: 'var(--space-2)', fontSize: 'var(--text-xs)' }}>
                    {[
                      { label: '5m', val: ep.return_5m },
                      { label: '15m', val: ep.return_15m },
                      { label: '1h', val: ep.return_1h },
                      { label: '4h', val: ep.return_4h },
                      { label: '24h', val: ep.return_24h },
                    ].map(({ label, val }) => (
                      <span key={label} style={{ color: val != null ? pctColor(val) : 'var(--text-tertiary)' }}>
                        {label}: {val != null ? formatPct(val) : '--'}
                      </span>
                    ))}
                  </div>
                  {/* 유사 에피소드 매칭 결과 */}
                  {ep.similar_episodes && ep.similar_episodes.count > 0 && (
                    <div style={{ marginTop: 'var(--space-2)', fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
                      유사 {ep.similar_episodes.count}건 매칭 |
                      {Object.entries(ep.similar_episodes.label_distribution || {}).map(([lbl, cnt]: [string, any]) => {
                        const cfg = LABEL_CONFIG[lbl];
                        return (
                          <span key={lbl} style={{ marginLeft: 4 }}>
                            {cfg?.icon || ''} {cfg?.label || lbl} {cnt}건
                          </span>
                        );
                      })}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* === 최근 에피소드 히스토리 === */}
      <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
        <div className="card-body" style={{ padding: 'var(--space-6)' }}>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-4)', fontWeight: 'var(--font-semibold)' }}>
            최근 에피소드
          </div>
          {recentEpisodes.length === 0 ? (
            <div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-sm)', textAlign: 'center', padding: 'var(--space-8) 0' }}>
              에피소드 데이터 수집 중...
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {recentEpisodes.map((ep: any) => {
                const cfg = ep.label ? LABEL_CONFIG[ep.label] : null;
                return (
                  <div
                    key={ep.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 'var(--space-3)',
                      padding: 'var(--space-3) var(--space-4)',
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--bg-secondary)',
                    }}
                  >
                    {cfg && (
                      <span style={{ fontSize: 'var(--text-sm)' }}>{cfg.icon}</span>
                    )}
                    <span
                      style={{
                        display: 'inline-block',
                        padding: '2px 8px',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: 'var(--text-xs)',
                        fontWeight: 'var(--font-semibold)',
                        color: '#fff',
                        background: cfg?.color || 'var(--text-tertiary)',
                        minWidth: 90,
                        textAlign: 'center',
                      }}
                    >
                      {cfg?.label || ep.label || 'tracking...'}
                    </span>
                    <span style={{ fontWeight: 'var(--font-semibold)', color: pctColor(ep.price_change_pct), minWidth: 50 }}>
                      {formatPct(ep.price_change_pct)}
                    </span>
                    <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
                      1h: <span style={{ color: pctColor(ep.return_1h) }}>{formatPct(ep.return_1h)}</span>
                    </span>
                    {ep.max_return != null && (
                      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
                        max: <span style={{ color: pctColor(ep.max_return) }}>{formatPct(ep.max_return)}</span>
                      </span>
                    )}
                    <span style={{ marginLeft: 'auto', color: 'var(--text-tertiary)', fontSize: 'var(--text-xs)', flexShrink: 0 }}>
                      {ep.detected_at ? timeAgo(ep.detected_at) : ''}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* === 축적 통계 === */}
      {whaleStats && whaleStats.total_episodes > 0 && (
        <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
          <div className="card-body" style={{ padding: 'var(--space-6)' }}>
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-3)', fontWeight: 'var(--font-semibold)' }}>
              축적 통계 (총 {whaleStats.total_episodes} 에피소드)
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {labelDist.map((ld: any) => {
                const cfg = LABEL_CONFIG[ld.label];
                const pct = whaleStats.completed_episodes > 0
                  ? (ld.count / whaleStats.completed_episodes * 100).toFixed(0)
                  : '0';
                return (
                  <div
                    key={ld.label}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 'var(--space-3)',
                      padding: 'var(--space-2) var(--space-4)',
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--bg-secondary)',
                    }}
                  >
                    <span style={{ fontSize: 'var(--text-sm)' }}>{cfg?.icon || ''}</span>
                    <span style={{ fontWeight: 'var(--font-semibold)', color: cfg?.color || 'var(--text-primary)', minWidth: 140 }}>
                      {cfg?.label || ld.label}
                    </span>
                    <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
                      {ld.count}건 ({pct}%)
                    </span>
                    <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginLeft: 'auto' }}>
                      avg max: <span style={{ color: pctColor(ld.avg_max_return) }}>{formatPct(ld.avg_max_return)}</span>
                      {' | '}
                      dd: <span style={{ color: pctColor(ld.avg_max_drawdown) }}>{formatPct(ld.avg_max_drawdown)}</span>
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* === 고래 거래 피드 === */}
      {whaleTrades.length > 0 && (
        <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
          <div className="card-body" style={{ padding: 'var(--space-6)' }}>
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-4)', fontWeight: 'var(--font-semibold)' }}>
              최근 고래 거래
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
              {whaleTrades.map((t: any, i: number) => (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-3)',
                    padding: 'var(--space-2) var(--space-3)',
                    fontSize: 'var(--text-sm)',
                  }}
                >
                  <span style={{
                    color: t.side === 'BUY' ? 'var(--green)' : 'var(--red)',
                    fontWeight: 'var(--font-semibold)',
                    minWidth: 36,
                  }}>
                    {t.side === 'BUY' ? 'BUY' : 'SELL'}
                  </span>
                  <span style={{ fontWeight: 'var(--font-semibold)', color: 'var(--text-primary)' }}>
                    {formatUsd(t.notional_usd)}
                  </span>
                  <span style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-xs)' }}>
                    @ ${t.price?.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </span>
                  <span style={{ marginLeft: 'auto', color: 'var(--text-tertiary)', fontSize: 'var(--text-xs)' }}>
                    {t.trade_time ? timeAgo(t.trade_time) : ''}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* === 신규 상장 현황 (기존) === */}
      <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
        <div className="card-body" style={{ padding: 'var(--space-6)' }}>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-3)', fontWeight: 'var(--font-semibold)' }}>
            신규 상장 현황
          </div>
          <div style={{ display: 'flex', gap: 'var(--space-8)' }}>
            <div>
              <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 'var(--font-bold)', color: 'var(--text-primary)' }}>
                {stats?.last_24h ?? '-'}
              </div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>24시간</div>
            </div>
            <div>
              <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 'var(--font-bold)', color: 'var(--text-primary)' }}>
                {stats?.last_7d ?? '-'}
              </div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>7일</div>
            </div>
            <div>
              <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 'var(--font-bold)', color: 'var(--text-primary)' }}>
                {stats?.last_30d ?? '-'}
              </div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>30일</div>
            </div>
          </div>
        </div>
      </div>

      {/* 최근 상장 목록 */}
      <div className="card">
        <div className="card-body" style={{ padding: 'var(--space-6)' }}>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginBottom: 'var(--space-4)', fontWeight: 'var(--font-semibold)' }}>
            최근 상장
          </div>
          {events.length === 0 ? (
            <div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-sm)', textAlign: 'center', padding: 'var(--space-8) 0' }}>
              상장 이벤트 없음
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {events.map((ev: any) => (
                <div
                  key={ev.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-3)',
                    padding: 'var(--space-3) var(--space-4)',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-secondary)',
                  }}
                >
                  <span
                    style={{
                      display: 'inline-block',
                      padding: '2px 8px',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: 'var(--text-xs)',
                      fontWeight: 'var(--font-semibold)',
                      color: '#fff',
                      background: ev.exchange === 'upbit' ? '#185abc' : '#e67e22',
                      flexShrink: 0,
                    }}
                  >
                    {ev.exchange === 'upbit' ? '업비트' : '빗썸'}
                  </span>
                  <span style={{ fontWeight: 'var(--font-semibold)', color: 'var(--text-primary)', minWidth: 60 }}>
                    {ev.symbol}
                  </span>
                  {ev.korean_name && (
                    <span style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
                      {ev.korean_name}
                    </span>
                  )}
                  <span style={{ marginLeft: 'auto', color: 'var(--text-tertiary)', fontSize: 'var(--text-xs)', flexShrink: 0 }}>
                    {ev.detected_at ? timeAgo(ev.detected_at) : ''}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default MarketOverviewPage;
