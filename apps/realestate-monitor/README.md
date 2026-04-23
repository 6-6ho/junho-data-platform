# Realestate Monitor — 성북구 월세 신규 매물 일일 알림

매일 08:00 KST, 서울 성북구에 **어제** 새로 올라온 투룸·쓰리룸 월세 매물을
직방·다방에서 모아 중복 제거 후 텔레그램으로 보낸다.

## 스펙

- 지역: 서울 성북구
- 타입: 투룸/쓰리룸 (빌라·다세대)
- 거래: 월세 / 보증금 ≤ 3,000만 / 월세 ≤ 120만
- 소스: 직방 + 다방 (네이버 제외 — 빌라 커버 약함, rate limit 타이트)
- 실행: GitHub Actions cron `0 23 * * *` UTC = 08:00 KST

## 구조

```
apps/realestate-monitor/
├── sources/
│   ├── zigbang.py   # geohash 기반 수집
│   └── dabang.py    # bbox 기반 수집
├── filters.py       # 날짜(어제 KST) / 가격 / 지역 필터
├── dedupe.py        # 직방-다방 중복 제거 (직방 우선)
├── notifier.py      # 텔레그램 전송
├── main.py          # 엔트리포인트
└── requirements.txt
```

## 로컬 실행

```bash
cd apps/realestate-monitor
cp .env.example .env   # 토큰 / 챗ID 채우기
pip install -r requirements.txt
python main.py
```

환경변수가 없으면 메시지를 stdout 에 그대로 출력하므로 dry-run 가능.

## 배포

GitHub Actions `.github/workflows/seongbuk-rental-daily.yml` 로 스케줄. 시크릿으로
`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` 등록 필요.

## ⚠️ API 주의

직방/다방 내부 API는 공식 문서가 없어 언제든 스키마가 바뀔 수 있다. 응답이 비면
브라우저 DevTools(Network → XHR)로 현재 요청을 확인하고 아래를 점검:

- 직방 `v2/items/villa` list → `v2/items/list` detail 흐름
- 다방 `api/3/room/list/multi-room/bbox` 페이로드 스키마
- `reg_date` 포맷 (타임존 표기 여부)
