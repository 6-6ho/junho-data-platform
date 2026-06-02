# junho-data-platform

Junho의 **개인 플랫폼**. 개인용 유틸 앱 3개를 laptop 노드 한 대에서 공유 Postgres + Cloudflare Tunnel로 운영한다.

> 원래 데이터 엔지니어링 쇼케이스(Trade 크립토 + Shop 이커머스, Kafka·Spark·Airflow 백본)였으나 2026-06 개인 플랫폼으로 슬림화. 이전 구조는 git history 참고.

## 앱

| 앱 | URL | 설명 |
|---|---|---|
| **realestate-monitor** | `6-6ho.com` | 성북구 일별 신규 매물 스크래핑 → DB → HTML 렌더 |
| **rag-server** (+ worker) | `rag.6-6ho.com/mcp` | 개인 RAG + MCP (Claude 커넥터). Voyage 임베딩 + pgvector |
| **todo** | `todo.6-6ho.com` | 개인 칸반 보드 + MCP. React 프론트 + FastMCP |

전부 Python(FastMCP/FastAPI) 기반이며 각자 **독립 Postgres 스키마**(`realestate` / `rag` / `todo`)로 격리된다.

## 인프라

- **postgres** (pgvector/pg16) — 공유 DB `app`, 앱별 스키마 격리
- **cloudflared** — Cloudflare Tunnel (`infra/tunnel/config.yml`)
- 단일 정의: `docker-compose.laptop.yml`

## 운영

```bash
docker compose -f docker-compose.laptop.yml up -d --build   # 배포 (laptop 로컬)
docker compose -f docker-compose.laptop.yml ps              # 상태 확인
```

배포는 laptop 본체에서 로컬 docker compose로 수행한다 (SSH/CI 없음).
