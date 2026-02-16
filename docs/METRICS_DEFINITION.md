# Business Metrics & Logic Definition

이 문서는 Shop Analytics 플랫폼에서 사용되는 주요 비즈니스 지표와 분석 로직의 정의를 기술합니다.

## 1. 📊 KPI Definitions

| Metric | Definition | Formula / Logic | Source |
|--------|------------|-----------------|--------|
| **Total Events** | 전체 사용자 행동 수 | `SUM(view_count + cart_count + purchase_count)` | `shop_brand_stats_log` |
| **Conversion Rate** | 구매 전환율 | `(Purchase Count / Page View Count) * 100` | `shop_funnel_stats_log` |
| **Top Brand** | 최고 매출 브랜드 | 24시간 내 `SUM(total_revenue)` 기준 1위 | `shop_brand_stats_log` |
| **Hourly Traffic** | 시간대별 트래픽 | `window_start`를 'Asia/Seoul'로 변환 후 시간별 집계 | `shop_brand_stats_log` |

---

## 2. 🛍️ Product Affinity Analysis (Market Basket)

사용자의 장바구니 패턴을 분석하여 연관 구매 규칙을 도출합니다.

- **Algorithm**: FP-Growth (Spark MLlib)
- **Data Source**: `shop_cart_log` (Grouping by `user_id`)
- **Metrics**:

### Rule Evaluation
`A` (Antecedent - 기준 상품) → `B` (Consequent - 연관 구매 상품)

1.  **Support (지지도)**
    - 전체 거래 중 A와 B가 함께 포함된 비율.
    - `Count(A & B) / Total Transactions`
    - *의미*: 이 규칙이 얼마나 흔하게 발생하는가?

2.  **Confidence (신뢰도)**
    - A를 포함한 거래 중 B도 포함될 확률.
    - `Count(A & B) / Count(A)`
    - *의미*: A를 샀을 때, B를 살 확률은? (추천 정확도)

3.  **Lift (향상도)**
    - A와 B가 우연히 같이 구매될 확률 대비 실제 같이 구매된 비율.
    - `Confidence(A→B) / Support(B)`
    - *의미*:
        - `> 1`: 양의 상관관계 (A가 B 구매를 촉진)
        - `= 1`: 독립 (관련 없음)
        - `< 1`: 음의 상관관계 (대체재 등)

---

## 3. 👥 RFM Customer Segmentation

사용자 가치를 평가하기 위해 구매 이력을 3가지 차원으로 분석합니다. (Recency, Frequency, Monetary)

### Dimensions
1.  **Recency (R)**: 얼마나 최근에 구매했는가? (`current_date - last_purchase_date`)
2.  **Frequency (F)**: 얼마나 자주 구매했는가? (`count(orders)`)
3.  **Monetary (M)**: 얼마나 많이 지출했는가? (`sum(amount)`)

### Scoring & Segmentation Logic
각 차원을 1~5점 척도로 변환(NTILE) 후 조합하여 세그먼트 부여.

| Segment | Logic (Score Condition) | Strategy |
|---------|-------------------------|----------|
| **VIP** | `R >= 4 AND F >= 4 AND M >= 4` | 최우수 고객 케어, 프리미엄 혜택 제공 |
| **Loyal** | `F >= 3` | 재구매 유도, 포인트 적립 |
| **Risk** | `R <= 2` | 이탈 위험군, 윈백 쿠폰 발송 |
| **New** | `R >= 4 AND F <= 2` | 신규 유입, 웰컴 혜택 |
| **Regular** | *Others* | 일반 고객 관리 |

---

## 4. 🧪 Chaos Mode (Data Simulation)

시스템 검증을 위해 인위적인 데이터 이상(Chaos)을 주입하는 모드입니다.

- **Trigger**: `CHAOS_MODE=true` (Environment Variable)
- **Effect**:
    - **Anomaly Price**: 1% 확률로 비정상 가격($1,000,000) 발생.
    - **Category/Payment Null**: 필수 필드 누락 시뮬레이션.
    - **High Latency**: 네트워크 지연 시뮬레이션.
