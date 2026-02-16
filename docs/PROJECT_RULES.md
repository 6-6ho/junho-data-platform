# Project Guidelines & Rules

이 문서는 **Junho Data Platform**의 프로젝트 구조, 역할 분담, 그리고 개발 워크플로우 규칙을 정의합니다.

## 1. 🏗️ System Architecture & Responsibilities

프로젝트는 목적에 따라 크게 3가지 도메인으로 구분됩니다.

| Domain | URL (Subdomain) | Role | Primary Features |
|--------|----------------|------|------------------|
| **Shop** | `shop.6-6ho.com` | **Analytics & Visualization** | • 쇼핑몰 데이터 분석 및 시각화<br>• Business Insight (Affinity, RFM)<br>• 관리자용 대시보드 |
| **Monitor** | `monitor.6-6ho.com` | **Performance & Validation** | • 시스템 성능 확인 (CPU/Mem)<br>• 데이터 처리 파이프라인 검증 (Data Quality)<br>• Spark/Kafka 상태 모니터링 |
| **Trade** | `trade.6-6ho.com` | **Investment & Trading** | • 실시간 코인 시세 및 등락 감지<br>• 투자 관련 기능 (Watchlist, Alerts)<br>• Trading Helper 도구 |

---

## 2. 🔄 Development Workflow

기능 개발은 완전성(Perfection)을 기준으로 진행하며, 검증된 코드만 메인 브랜치에 반영합니다.

### Cycle
1.  **Feature Implementation**: 로컬 환경에서 기능 개발 및 테스트 완료.
2.  **Verification**: 
    - **Shop/Trade**: Web App UI에서 기능 작동 확인.
    - **Monitor**: Grafana 혹은 API를 통해 데이터 적재 및 성능 확인.
3.  **Docker Build**: 컨테이너 빌드 및 로컬 배포 테스트 (`docker compose up --build`).
4.  **Push**: 모든 검증이 끝나면 GitHub에 Push.

---

## 3. 📝 Commit Convention

명확한 히스토리 관리를 위해 **Conventional Commits** 규칙을 따릅니다.

### Format
`type(scope): subject`

### Types
- `feat`: 새로운 기능 추가 (Features)
- `fix`: 버그 수정 (Bug fixes)
- `docs`: 문서 수정 (Documentation)
- `style`: 코드 포맷팅, 세미콜론 누락 등 (System logic 영향 없음)
- `refactor`: 리팩토링 (기능 변화 없음)
- `test`: 테스트 코드 추가/수정
- `chore`: 빌드 태스크, 패키지 매니저 설정 등

### Examples
- `feat(shop): add product affinity page`
- `fix(spark): resolve streaming job memory leak`
- `docs(readme): add architecture diagram`
- `refactor(trade): optimize websocket connection`
