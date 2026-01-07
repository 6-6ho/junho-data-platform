# 프로젝트 개요

## 목적
- 바이낸스 선물(USDT-M Perp) 모바일의 Top Movers 중 **Rise**, **Price up with High Vol**만 PC(데스크탑 브라우저)에서 지속 모니터링한다.
- TradingView급 추세선 드로잉(드래그/편집/삭제) + 돌파/이탈 알럿을 결합한 “데이터 제품”을 만든다.
- 노트북(서버)에서 배포하고, 데스크탑에서 단일 포트(예: 3000)로 접속해 사용한다.

## 핵심 사용자 흐름
1) **Top Movers 탭**에서 Rise/HighVolUp 이벤트 Top 20을 훑는다.
2) 종목 클릭 → **Chart & Alerts 탭**으로 이동(심볼 자동 선택).
3) 차트 위에 추세선을 **드래그로 그려서** 알럿을 켠다.
4) 돌파/이탈 발생 시 알럿 이벤트가 생성되고 피드/저장소에 기록된다.

## 범위(딱 이거만)
- 대상: Binance Futures **USDT-M Perpetual만**
- Top Movers 카테고리:
  - Rise (5m, 2h)
  - Price up with High Vol (15m)
- 리스트: 각 카테고리 **Top 20**, 최신 이벤트 우선
- 알럿(v1): **close 기준**, crossing 이벤트 1회 + buffer + cooldown

## 제외
- Fall / Pullback / Rally / New High/Low / Price down with High Vol 전부 제외
- COIN-M 제외
- v1에서 wick(high/low) 기준 알럿 제외(v2 백로그)
