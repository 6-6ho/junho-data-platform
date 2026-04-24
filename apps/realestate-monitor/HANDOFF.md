# 성북구 월세 봇 — 인수인계 문서

다른 대화에서 이어서 작업하기 위한 현재 상태·남은 작업·맥락 정리.

---

## TL;DR (30초 컷)

- **브랜치**: `claude/seongbuk-rental-bot-fg3UK` (레포: `6-6ho/junho-data-platform`)
- **상태**: 코드 작성 + 랩탑 docker-compose 등록 완료, **실제 배포 미실행**
- **블로커**:
  1. `main` 머지 전 확인 필요 (`deploy.yml` 이 랩탑+데스크톱 전체를 재빌드)
  2. 직방/다방 API 스키마 실제 검증 안 됨 (스펙 추정 기반)
- **다음 할 일**: 랩탑에서 `RUN_ONCE=true` 로 dry-run → API 응답 확인 → 필요 시 `_normalize()` 수정 → main 머지

---

## 이 봇이 하는 일

매일 **08:00 KST**, 서울 **성북구**에 **어제** 등록된 **투룸/쓰리룸 월세** (빌라·다세대)
매물을 직방·다방에서 긁어다가 중복 제거하고 텔레그램으로 보냄.

| 항목 | 값 |
|---|---|
| 지역 | 서울 성북구 (bbox: 37.575~37.635 / 126.995~127.060) |
| 타입 | 투룸/쓰리룸 (빌라·다세대) |
| 거래 | 월세 |
| 보증금 | ≤ 3,000만 |
| 월세 | ≤ 120만 |
| 날짜 필터 | `reg_date` = 어제 KST 00:00 ~ 24:00 (±1일 슬랙) |
| 예상 볼륨 | 하루 5~20건 |
| 소스 | 직방 + 다방 (네이버 제외 — 빌라 커버 약함, rate limit 타이트) |
| 실행 방식 | 랩탑 docker-compose 데몬, 내부 스케줄러가 08:00 KST 기상 |

---

## 파일 구조

```
apps/realestate-monitor/
├── Dockerfile               # python:3.11-slim, TZ=Asia/Seoul
├── requirements.txt         # requests, python-dotenv (geohash 는 인라인 구현)
├── main.py                  # 데몬 루프 + run_daily()
├── filters.py               # 날짜(어제 KST) / 가격 / 지역 필터
├── dedupe.py                # (주소, 면적, 보증금, 월세) 키로 dedup — 직방 우선
├── notifier.py              # 텔레그램 Markdown + 4096자 청크 분할
├── README.md                # 사용법
├── HANDOFF.md               # ← 지금 이 파일
└── sources/
    ├── __init__.py
    ├── zigbang.py           # 직방: geohash 기반 list → detail 2단계 조회
    └── dabang.py            # 다방: bbox POST 1회
```

### 외부 영향

- `docker-compose.laptop.yml` — `realestate-monitor` 서비스 추가 (journal-bot 옆, 96M / 0.1CPU)
- `.env.example` 루트 — `REALESTATE_BOT_TOKEN` / `REALESTATE_CHAT_ID` 블록 추가

---

## 배포 플로우

### 현재 설정

기존 `.github/workflows/deploy.yml` 이 `main` 푸시 시 동작:

1. GH Actions → 랩탑 SSH 접속 (secrets: SSH_HOST/USER/PASSWORD/PORT)
2. `git fetch origin main && git reset --hard origin/main`
3. `docker compose -f docker-compose.laptop.yml down`
4. `docker compose -f docker-compose.laptop.yml up -d --build` ← 여기서 `realestate-monitor` 도 같이 올라감
5. `./deploy_desktop.sh` 실행 (데스크톱까지 연쇄 배포)

즉, **main 머지 = 전체 스택 재빌드**. 무거움.

### main 머지 전에 해야 할 것 (권장 순서)

1. 랩탑에서 브랜치 직접 pull 해서 `realestate-monitor` 만 단독 빌드/기동
2. `RUN_ONCE=true` 로 1회 실행해서 API 응답 확인
3. 응답 스키마가 추정과 다르면 `sources/*.py` 의 `_normalize()` 수정
4. dry-run 성공 확인 후 main 머지

```bash
# 랩탑 SSH 접속 후
cd ~/junho-data-platform   # 실제 경로 확인
git fetch origin
git checkout claude/seongbuk-rental-bot-fg3UK
git pull

# .env 에 토큰 추가 (루트 .env)
#   REALESTATE_BOT_TOKEN=... (없으면 TELEGRAM_BOT_TOKEN 폴백)
#   REALESTATE_CHAT_ID=...

# 1회 dry-run (토큰 없어도 stdout 으로 메시지 출력)
docker compose -f docker-compose.laptop.yml build realestate-monitor
docker compose -f docker-compose.laptop.yml run --rm \
  -e RUN_ONCE=true realestate-monitor

# 검증 OK 면 데몬으로 기동
docker compose -f docker-compose.laptop.yml up -d --build realestate-monitor
docker compose -f docker-compose.laptop.yml logs -f realestate-monitor
```

정상이면 로그에 이런 줄이 찍힘:
```
realestate-monitor 시작 (매일 08:00 KST 실행)
다음 실행: 2026-04-25T08:00:00+09:00 KST (11.8시간 뒤)
```

---

## 환경변수 (루트 `.env`)

| 키 | 필수 | 설명 |
|---|---|---|
| `REALESTATE_BOT_TOKEN` | - | 전용 봇 토큰. 비우면 `TELEGRAM_BOT_TOKEN` 폴백 |
| `REALESTATE_CHAT_ID` | - | 전용 채팅 ID. 비우면 `TELEGRAM_CHAT_ID` 폴백 |
| `RUN_HOUR_KST` | - | 기본 `8` |
| `RUN_MINUTE_KST` | - | 기본 `0` |
| `RUN_ONCE` | - | `true` 면 1회 실행 후 종료 (수동 검증용) |

**채팅 분리 권장**: `listing-monitor` 가 이미 `TELEGRAM_*` 로 코인 상장 알림을 보내고 있음.
월세 알림이 거기 섞이면 지저분하니 전용 봇/챗 만들어서 `REALESTATE_*` 로 주입 권장.

---

## 현재 미검증 항목 (반드시 첫 실행 때 확인)

### 1. 직방 API

- 엔드포인트 가정:
  - list: `GET https://apis.zigbang.com/v2/items/villa?geohash=...`
  - detail: `POST https://apis.zigbang.com/v2/items/list` (body: `{item_ids, domain, withCoalition}`)
- 확인 방법: 브라우저에서 직방 → 성북구 → 빌라/투쓰리룸/월세 설정 → F12 Network → XHR
- 응답 필드 이름 바뀌어 있으면 `sources/zigbang.py:_normalize()` 매핑 고치면 끝

### 2. 다방 API

- 엔드포인트 가정: `POST https://www.dabangapp.com/api/3/room/list/multi-room/bbox`
- 페이로드: `filters.multi_room_type=[1,2]`, `deposit_range`, `price_range` 등
- 응답 구조 후보 여러 개 두고 `rooms` / `result.rooms` / `items` 순으로 파싱 중
- 마찬가지로 DevTools 확인 후 `sources/dabang.py:_normalize()` 매핑 수정

### 3. `reg_date` 포맷/타임존

- 현재 `filters.py` 가 ISO / 에포크(s/ms) / `YYYY-MM-DD` 여러 포맷 시도
- 파싱 실패 시 보수적으로 **통과** 처리 → 날짜 필터가 의미 없을 수 있음
- 첫 실행 때 원본 몇 개 로그에 찍어보고 포맷 확정 필요

### 4. geohash 커버리지

- 성북구 bbox 를 prec=5 geohash 6개로 커버 (`wydmc`, `wydmf`, `wydmg`, `wydq1`, `wydq4`, `wydq5`)
- 경계 밖 매물 섞일 수 있어서 주소 문자열에 "성북구" 포함 여부로 2차 필터 이미 적용
- 만약 수집 후보 0건이면 geohash 커버리지나 파라미터 문제

---

## 검증 체크리스트

첫 실행 때 이 순서로 확인:

- [ ] `RUN_ONCE=true` dry-run 에서 로그에 "직방: 수집 N건" / "다방: 수집 N건" 찍히는지 (N > 0)
- [ ] 필터 통과 건수가 비현실적이지 않은지 (하루 5~20건 예상. 0 또는 수백 이면 뭔가 틀림)
- [ ] 중복 제거 전/후 비율 (겹침 ~90% 예상이라 거의 절반 줄어야 함)
- [ ] 텔레그램 메시지에 보증금/월세/면적/주소/URL 제대로 들어가는지
- [ ] URL 클릭 시 실제 매물 페이지 열리는지 (직방 item_id 경로, 다방 room_id 경로)
- [ ] 컨테이너 재시작 후 다음 날 08:00 KST 에 실제로 실행되는지 (다음 실행 로그 확인)

---

## 자주 발생할 이슈 대응

| 증상 | 원인 후보 | 대응 |
|---|---|---|
| 직방 0건 | 엔드포인트/파라미터 변경 | DevTools 재확인 → `sources/zigbang.py` 수정 |
| 다방 0건 | bbox 값 또는 페이로드 스키마 변경 | 동일 — `sources/dabang.py` |
| 건수 너무 많음 | 날짜 필터 파싱 실패해 전체 통과 | `filters.py:_to_kst_date()` 디버그, raw 샘플 로그 |
| 중복제거 비율 낮음 | 주소 포맷 차이 | `dedupe.py:normalize_address()` 더 공격적으로 |
| 텔레그램 메시지 안 옴 | 토큰/챗ID 미설정 | 로그 확인, stdout 폴백됐으면 env 문제 |
| 08:00 에 안 뜸 | TZ 오설정 | 컨테이너에 `TZ=Asia/Seoul` 들어갔는지, compose 에 설정 있음 |

---

## 다음 대화에서 바로 쓸 수 있는 프롬프트

> 성북구 월세 봇 인수인계.
> 브랜치: `claude/seongbuk-rental-bot-fg3UK`
> `apps/realestate-monitor/HANDOFF.md` 읽어보고,
> 랩탑에서 `RUN_ONCE=true` 로 dry-run 했더니 [여기에 로그 붙여넣기]
> [직방|다방] API 스키마가 추정과 다른 것 같으니 `sources/[파일].py` 의 `_normalize()` 고쳐줘.

또는

> 성북구 월세 봇 (`claude/seongbuk-rental-bot-fg3UK` 브랜치).
> dry-run 성공했으니 main 에 머지해서 자동 배포 태워줘.
> PR 생성 → squash merge → Actions 로그 확인까지.

---

## 관련 커밋

- `a69c14a` feat: 성북구 월세 신규 매물 일일 알림 봇 (realestate-monitor) — 초기 구현 + GH Actions
- `07d48d2` refactor(realestate-monitor): GH Actions → 랩탑 docker-compose 배포로 전환

브랜치는 `origin/claude/seongbuk-rental-bot-fg3UK` 에 푸시돼 있음.
