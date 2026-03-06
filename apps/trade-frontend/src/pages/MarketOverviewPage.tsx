function MarketOverviewPage() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
      <div className="card" style={{ maxWidth: 480, width: '100%', textAlign: 'center' }}>
        <div className="card-body" style={{ padding: 'var(--space-10)' }}>
          <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 'var(--font-bold)', color: 'var(--text-primary)', marginBottom: 'var(--space-4)' }}>
            Coming Soon
          </div>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', lineHeight: 1.8 }}>
            주요 지수 현황 (S&P 500, NASDAQ, KOSPI)<br />
            Fear &amp; Greed Index<br />
            자산군별 상관관계<br />
            글로벌 매크로 지표
          </div>
        </div>
      </div>
    </div>
  );
}

export default MarketOverviewPage;
