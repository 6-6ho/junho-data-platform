# Product Spec

## 1) 단일 포트 웹앱
- 단일 포트(예: 3000)에서 탭 2개 제공
  - `/movers`: Top Movers
  - `/chart?symbol=BTCUSDT`: 차트/드로잉/알럿
- 외부 노출 포트는 **1개만**(프론트 Nginx). 백엔드/카프카/스파크/DB/MinIO는 내부 네트워크로만.

## 2) Top Movers (USDT-M Perp)
- 2컬럼 카드 레이아웃
  - Left: **Rise Top 20**
  - Right: **High Vol Up Top 20**
- 각 Row 표시(모바일 느낌의 컴팩트 리스트):
  - `symbol` + `Perp` 배지
  - `24h change(%)`
  - `status label` (예: `[Mid] 5 min Rise`, `[Small] Price up with High Vol`)
  - `event time` (조건이 성립한 시각)
- 정렬: **최신 이벤트 우선**
- 갱신: 기본 5초 폴링 + auto refresh 토글 + last update 시각 표기
- 동작: Row 클릭 시 `/chart?symbol=XXX`로 이동

## 3) Chart + Trendline Drawing (TradingView-like)
- 차트: 캔들 + 거래량
- 드로잉 UX(v1)
  - 선 생성: 클릭-드래그
  - 선 선택
  - 선 이동
  - 끝점(핸들) 드래그로 각도/길이 조절
  - 삭제
  - 라인 목록 패널(현재 심볼의 라인들)
- 알럿(v1)
  - 라인별 enabled 토글
  - 모드: 상향 돌파 / 하향 이탈 / 둘 다
  - 기준: **close-only**
  - `buffer_pct` 기본 0.1% (노이즈 방지)
  - `cooldown_sec` 기본 600초 (중복 방지)
  - 트리거: **crossing 이벤트(직전 below → 현재 above)** 같은 “교차”만 1회 발생
- 알럿 피드: 최근 50개 이벤트 리스트 표시

## 4) 지속성
- 라인 설정은 서버(Postgres)에 저장되어 새로고침 후에도 유지
- 알럿 이벤트는 저장(최소 최근 N개 조회 가능)
