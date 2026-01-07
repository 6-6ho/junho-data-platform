# Binance Movers + Trendline Alerts (USDT-M Perp)

## 개요
- 단일 포트(3000)로 접속하는 웹앱
  - Top Movers: Rise / HighVolUp 각각 Top 20
  - Chart & Alerts: 트뷰급 추세선 드로잉 + 돌파/이탈 알럿(v1 close-only)

## 실행(예시)
```bash
docker compose up -d
# 브라우저: http://localhost:3000
```

## 데모 시나리오
1) `/movers` 탭에서 Rise/HighVolUp Top20 확인
2) 심볼 클릭 → `/chart?symbol=XXX` 이동
3) 추세선 드래그로 생성 후 enabled
4) 가격이 추세선을 돌파/이탈하면 alerts feed에 이벤트 생성 확인

## 완료 기준(DoD)
- 외부 노출 포트는 3000 하나뿐
- `/movers`에서 Rise/HighVolUp 각각 Top20이 자동 갱신
- `/chart`에서 라인 드로잉/편집/삭제 가능 + 새로고침 후 유지
- 알럿 이벤트가 생성되고 피드에 표시 + 저장됨
- 1시간 이상 안정 실행

## 백로그(v2)
- wick(high/low) 기준 알럿
- 스냅(OHLC/시간) 옵션
- 텔레그램/디스코드 알림 채널
- 일간 PDF 리포트 + Airflow DAG
