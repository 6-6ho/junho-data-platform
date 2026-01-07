# UI Spec

## 공통
- 상단 탭 네비게이션: `[Top Movers] [Chart & Alerts]`
- 헤더: `Last update` + `Auto refresh ON/OFF`

## 1) /movers (Top Movers 탭)
- 레이아웃: 2컬럼 카드
  - 좌: Rise (Top 20)
  - 우: Price up with High Vol (Top 20)
- Row 구성(한 줄)
  - 심볼 + Perp 배지
  - 24h change(%)
  - status 라벨
  - event time
- 정렬: 최신 이벤트가 상단
- Row 클릭 → `/chart?symbol=XXX` 이동

## 2) /chart (Chart & Alerts 탭)
### 좌측: 차트 영역
- 캔들 + 거래량 바
- timeframe selector: 1m/5m/15m/1h
- crosshair/tooltip

### 우측: 라인/알럿 패널
- 라인 목록
- 선택 라인 설정:
  - enabled 토글
  - mode: break_up / break_down / both
  - buffer_pct
  - cooldown_sec
- 알럿 이벤트 피드(최근 50개)

## UX 디테일(권장)
- 새 라인 생성 시 즉시 저장(autosave)
- 삭제 시 확인(옵션)
- 심볼 전환 시 해당 심볼의 라인을 로드
