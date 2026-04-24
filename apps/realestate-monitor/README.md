# Realestate Monitor — 성북구 월세 신규 매물 일일 알림

매일 08:00 KST, 서울 성북구에 **어제** 새로 올라온 투룸·쓰리룸 월세 매물을
직방·다방에서 모아 중복 제거 후 텔레그램으로 보낸다.

## 스펙

- 지역: 서울 성북구
- 타입: 투룸/쓰리룸 (빌라·다세대)
- 거래: 월세 / 보증금 ≤ 3,000만 / 월세 ≤ 120만
- 소스: 직방 + 다방 (네이버 제외 — 빌라 커버 약함, rate limit 타이트)
- 실행: 랩탑 docker-compose 서비스, 내부 스케줄러가 매일 08:00 KST 기상

## 구조

```
apps/realestate-monitor/
├── Dockerfile
├── requirements.txt
├── main.py          # 데몬 루프 (08:00 KST 기상)
├── filters.py       # 날짜(어제 KST) / 가격 / 지역 필터
├── dedupe.py        # 직방-다방 중복 제거 (직방 우선)
├── notifier.py      # 텔레그램 전송
└── sources/
    ├── zigbang.py   # geohash 기반 수집
    └── dabang.py    # bbox 기반 수집
```

## 배포 (랩탑)

`docker-compose.laptop.yml` 에 서비스 등록되어 있음. `.github/workflows/deploy.yml`
의 기존 파이프라인(SSH → pull → `docker compose up -d --build`) 에 자동으로 포함된다.

```bash
# 랩탑에서 수동 재기동
docker compose -f docker-compose.laptop.yml up -d --build realestate-monitor
docker compose -f docker-compose.laptop.yml logs -f realestate-monitor
```

## 환경변수 (루트 `.env`)

| 키 | 설명 |
|---|---|
| `REALESTATE_BOT_TOKEN` | 전용 봇 토큰. 비우면 `TELEGRAM_BOT_TOKEN` 폴백 |
| `REALESTATE_CHAT_ID` | 전용 채팅 ID. 비우면 `TELEGRAM_CHAT_ID` 폴백 |
| `RUN_HOUR_KST` (opt) | 기본 8 |
| `RUN_MINUTE_KST` (opt) | 기본 0 |
| `RUN_ONCE` (opt) | `true` 면 1회 실행 후 종료 (수동 검증용) |

## 수동 1회 실행

```bash
# 컨테이너 내부에서
docker compose -f docker-compose.laptop.yml run --rm -e RUN_ONCE=true realestate-monitor
```

봇 토큰/챗ID 미설정이면 stdout 으로만 메시지를 뽑으므로 dry-run 으로도 쓸 수 있다.

## ⚠️ API 주의

직방/다방 내부 API는 공식 문서가 없어 언제든 스키마가 바뀔 수 있다. 응답이 비면
브라우저 DevTools(Network → XHR)로 현재 요청을 확인하고 아래를 점검:

- 직방 `v2/items/villa` list → `v2/items/list` detail 흐름
- 다방 `api/3/room/list/multi-room/bbox` 페이로드 스키마
- `reg_date` 포맷 (타임존 표기 여부)
