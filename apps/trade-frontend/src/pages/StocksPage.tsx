function StocksPage() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
      <div className="card" style={{ maxWidth: 480, width: '100%', textAlign: 'center' }}>
        <div className="card-body" style={{ padding: 'var(--space-10)' }}>
          <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 'var(--font-bold)', color: 'var(--text-primary)', marginBottom: 'var(--space-4)' }}>
            Coming Soon
          </div>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', lineHeight: 1.8 }}>
            한국 주식 섹터별 모니터링<br />
            미국 주식 Top Movers<br />
            ETF 흐름 추적<br />
            실적 캘린더
          </div>
        </div>
      </div>
    </div>
  );
}

export default StocksPage;
