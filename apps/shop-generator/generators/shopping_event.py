"""
Shopping Event Generator

Generates realistic e-commerce shopping events:
- search: Product search
- view: Product detail view
- add_cart: Add to cart
- purchase: Complete purchase

User personas (realistic distribution):
- heavy_buyer (10%): purchase-oriented, frequent orders
- browser     (50%): search/view-heavy, rare purchases
- occasional  (40%): balanced, default funnel weights
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import Literal, Optional

from faker import Faker
from pydantic import BaseModel, Field
import psycopg2
from config import get_settings

fake = Faker('ko_KR')


# --- Pydantic Data Contract ---

class DeviceInfo(BaseModel):
    type: Literal["mobile", "desktop", "tablet"]
    os: str
    app_version: str


class CampaignInfo(BaseModel):
    id: str
    name: str


class ContextInfo(BaseModel):
    referrer: str
    campaign: Optional[CampaignInfo] = None


class ShoppingEvent(BaseModel):
    """Data Contract for shopping events sent to Kafka."""
    event_id: str
    event_type: Literal["search", "view", "add_cart", "purchase"]
    user_id: str
    product_id: str
    product_name: str
    category: str
    brand: str
    price: float = Field(gt=0)
    timestamp: str
    session_id: str
    device: DeviceInfo
    context: ContextInfo
    quantity: Optional[int] = None
    total_amount: Optional[float] = None
    payment_method: Optional[str] = None


class ShoppingEventGenerator:

    # Product categories and items
    CATEGORIES = {
        'fashion': {
            'items': ['운동화', '청바지', '티셔츠', '원피스', '자켓', '코트', '가방', '모자'],
            'brands': ['나이키', '아디다스', '뉴발란스', '유니클로', '자라', '폴로'],
            'price_range': (30000, 300000)
        },
        'electronics': {
            'items': ['이어폰', '노트북', '태블릿', '스마트워치', '키보드', '마우스', '모니터'],
            'brands': ['삼성', '애플', 'LG', '소니', '로지텍', '레노버'],
            'price_range': (50000, 2000000)
        },
        'beauty': {
            'items': ['립스틱', '파운데이션', '스킨케어', '선크림', '마스크팩', '향수'],
            'brands': ['이니스프리', '설화수', '라네즈', '에스티로더', '맥'],
            'price_range': (10000, 200000)
        },
        'food': {
            'items': ['과자', '음료', '커피', '라면', '간식', '건강식품'],
            'brands': ['오리온', '롯데', '농심', 'CJ', '해태'],
            'price_range': (1000, 50000)
        },
        'home': {
            'items': ['침구', '수납함', '조명', '커튼', '식기', '주방용품'],
            'brands': ['이케아', '한샘', '리바트', '까사미아'],
            'price_range': (10000, 500000)
        }
    }

    EVENT_TYPES = ['search', 'view', 'add_cart', 'purchase']

    # Conversion funnel probabilities
    EVENT_WEIGHTS = [0.40, 0.35, 0.15, 0.10]  # search > view > cart > purchase

    DEVICE_TYPES = ['mobile', 'desktop', 'tablet']
    DEVICE_WEIGHTS = [0.65, 0.30, 0.05]  # Mobile dominant

    OS_BY_DEVICE = {
        'mobile': ['iOS', 'Android'],
        'desktop': ['Windows', 'macOS', 'Linux'],
        'tablet': ['iOS', 'Android']
    }

    REFERRERS = ['direct', 'google_search', 'instagram', 'facebook', 'youtube', 'blog', 'email']

    # Per-persona event weights: [search, view, add_cart, purchase]
    PERSONA_WEIGHTS = {
        'heavy_buyer': [0.15, 0.30, 0.25, 0.30],
        'browser':     [0.50, 0.35, 0.10, 0.05],
        'occasional':  [0.40, 0.35, 0.15, 0.10],  # same as default EVENT_WEIGHTS
    }

    def __init__(self, chaos_mode: bool = False):
        self.settings = get_settings()
        self.chaos_mode = getattr(self.settings, 'CHAOS_MODE', chaos_mode)
        self.category_bias = None
        self.persona_bias = None
        self.product_cache = self._load_products_from_db()
        if not self.product_cache:
            print("⚠️ DB Connection failed or empty. Fallback to synthetic products.")
            self.product_cache = self._generate_product_catalog()
        else:
            print(f"✅ Loaded {len(self.product_cache)} products from Database.")
        self.user_pool = [f"u_{uuid.uuid4().hex[:8]}" for _ in range(10000)]

        # Assign persona to each user (heavy_buyer 10%, browser 50%, occasional 40%)
        self.user_personas = {
            uid: random.choices(
                ['heavy_buyer', 'browser', 'occasional'],
                weights=[0.10, 0.50, 0.40],
            )[0]
            for uid in self.user_pool
        }
        persona_counts = {}
        for p in self.user_personas.values():
            persona_counts[p] = persona_counts.get(p, 0) + 1
        print(f"👤 User personas: {persona_counts}")

        self.failed_payments = set()        # 장애 난 결제수단
        self.failed_categories = set()     # 장애 난 카테고리
        self._chaos_check_counter = 0       # 장애 상태 변경 주기 관리

        self.active_sessions = {}           # user_id → {session_id, expires_at}
        self._event_counter = 0             # 만료 세션 정리 주기 관리

        self.last_reload_time = datetime.now()
        self.RELOAD_INTERVAL = 3600 # 1 hour

    def _load_products_from_db(self):
        """Attempt to load products from Postgres table 'shop_product'."""
        products = []
        try:
            conn = psycopg2.connect(
                host=self.settings.DB_HOST,
                database=self.settings.POSTGRES_DB,
                user=self.settings.POSTGRES_USER,
                password=self.settings.POSTGRES_PASSWORD
            )
            cur = conn.cursor()
            cur.execute("SELECT product_id, name, category, price FROM shop_product")
            rows = cur.fetchall()
            
            for row in rows:
                products.append({
                    'product_id': str(row[0]),
                    'name': row[1],
                    'category': row[2],
                    'brand': 'Premium', # DB에 브랜드 컬럼이 없어서 임시 지정
                    'item_type': row[2],
                    'price': row[3]
                })
            
            cur.close()
            conn.close()
            return products
        except Exception as e:
            print(f"❌ DB Loading Error: {e}")
            return []

    def _generate_product_catalog(self, num_products=1000):
        """Pre-generate product catalog for consistency."""
        products = []
        for i in range(num_products):
            category = random.choice(list(self.CATEGORIES.keys()))
            cat_info = self.CATEGORIES[category]

            item = random.choice(cat_info['items'])
            brand = random.choice(cat_info['brands'])
            price = random.randint(*cat_info['price_range'])

            products.append({
                'product_id': f"pd_{i:06d}",
                'name': f"{brand} {item}",
                'category': category,
                'brand': brand,
                'item_type': item,
                'price': price
            })

        return products

    def _get_or_create_session(self, user_id: str) -> str:
        """유저별 세션 영속성: 5~30분간 같은 session_id 유지"""
        now = datetime.now()
        if user_id in self.active_sessions:
            session = self.active_sessions[user_id]
            if now < session['expires_at']:
                return session['session_id']

        # 새 세션 생성
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        duration = timedelta(minutes=random.randint(5, 30))
        self.active_sessions[user_id] = {
            'session_id': session_id,
            'expires_at': now + duration
        }
        return session_id

    def _cleanup_expired_sessions(self):
        """매 1000 이벤트마다 만료된 세션 정리"""
        self._event_counter += 1
        if self._event_counter < 1000:
            return
        self._event_counter = 0
        now = datetime.now()
        expired = [uid for uid, s in self.active_sessions.items() if now >= s['expires_at']]
        for uid in expired:
            del self.active_sessions[uid]

    def _simulate_failures(self):
        """장애 상황 시뮬레이션 (매 100 이벤트마다 상태 변경 검토)"""
        self._chaos_check_counter += 1
        if self._chaos_check_counter < 100:
            return
        self._chaos_check_counter = 0
        
        # 3% 확률로 카테고리 장애 발생
        if random.random() < 0.03:
            available_categories = set(self.CATEGORIES.keys()) - self.failed_categories
            if available_categories:
                category = random.choice(list(available_categories))
                self.failed_categories.add(category)
                print(f"[CHAOS] 🔴 Category failure: {category}")
        
        # 5% 확률로 카테고리 복구
        if self.failed_categories and random.random() < 0.05:
            recovered = self.failed_categories.pop()
            print(f"[CHAOS] 🟢 Category recovered: {recovered}")
        
        # 2% 확률로 결제수단 장애
        if random.random() < 0.02:
            payments = ['kakao_pay', 'naver_pay', 'toss']
            available_payments = set(payments) - self.failed_payments
            if available_payments:
                payment = random.choice(list(available_payments))
                self.failed_payments.add(payment)
                print(f"[CHAOS] 🔴 Payment failure: {payment}")
        
        # 7% 확률로 결제수단 복구
        if self.failed_payments and random.random() < 0.07:
            recovered = self.failed_payments.pop()
            print(f"[CHAOS] 🟢 Payment recovered: {recovered}")

    def generate(self) -> dict | None:
        """Generate a single shopping event. Returns None if dropped by chaos mode."""
        
        # Cleanup expired sessions periodically
        self._cleanup_expired_sessions()

        # Chaos Mode: 장애 상태 업데이트
        if self.chaos_mode:
            self._simulate_failures()
            
        # Check for product reload
        if (datetime.now() - self.last_reload_time).total_seconds() > self.RELOAD_INTERVAL:
            print("🔄 Reloading product catalog from DB...")
            new_products = self._load_products_from_db()
            if new_products:
                self.product_cache = new_products
                print(f"✅ Reloaded {len(self.product_cache)} products.")
            self.last_reload_time = datetime.now()

        # Select user first (persona determines event weights)
        user_id = random.choice(self.user_pool)
        
        # Override Persona if specified by Admin
        if self.persona_bias and random.random() < 0.8: # 80% forced override
            persona = self.persona_bias
        else:
            persona = self.user_personas.get(user_id, 'occasional')
            
        weights = self.PERSONA_WEIGHTS.get(persona, self.PERSONA_WEIGHTS['occasional'])

        # Select event type based on persona weights
        event_type = random.choices(self.EVENT_TYPES, weights=weights)[0]

        # Select product with Category Bias Support
        if self.category_bias and random.random() < 0.7:  # 70% chance to force category
            biased_products = [p for p in self.product_cache if p['category'] == self.category_bias]
            if biased_products:
                product = random.choice(biased_products)
            else:
                product = random.choice(self.product_cache)
        else:
            product = random.choice(self.product_cache)

        # Chaos Mode: 장애 난 카테고리면 데이터 누락!
        if self.chaos_mode and product['category'] in self.failed_categories:
            return None

        # Generate device info
        device_type = random.choices(self.DEVICE_TYPES, weights=self.DEVICE_WEIGHTS)[0]
        os = random.choice(self.OS_BY_DEVICE[device_type])
        
        # Get price (with possible chaos corruption)
        price = product['price']
        
        # Chaos Mode: 1% 확률로 이상 가격 생성 (버그 시뮬레이션)
        if self.chaos_mode and random.random() < 0.01:
            price = random.choice([-100, 0, 99999999])  # 비정상 가격

        # Generate event
        event = {
            'event_id': f"ev_{uuid.uuid4().hex}",
            'event_type': event_type,
            'user_id': user_id,
            'product_id': product['product_id'],
            'product_name': product['name'],
            'category': product['category'],
            'brand': product['brand'],
            'price': price,
            'timestamp': datetime.now().isoformat(),
            'session_id': self._get_or_create_session(user_id),
            'device': {
                'type': device_type,
                'os': os,
                'app_version': f"{random.randint(1,5)}.{random.randint(0,9)}.{random.randint(0,9)}"
            },
            'context': {
                'referrer': random.choice(self.REFERRERS),
                'campaign': self._generate_campaign() if random.random() < 0.3 else None
            }
        }

        # Add event-specific fields
        if event_type == 'purchase':
            event['quantity'] = random.randint(1, 3)
            event['total_amount'] = price * event['quantity']
            payment_method = random.choice(['card', 'kakao_pay', 'naver_pay', 'toss'])

            # Chaos Mode: 장애 난 결제수단이면 purchase 누락!
            if self.chaos_mode and payment_method in self.failed_payments:
                return None

            event['payment_method'] = payment_method
        elif event_type == 'add_cart':
            event['quantity'] = random.randint(1, 5)

        # Pydantic validation (skip for chaos-corrupted prices)
        is_chaos_price = self.chaos_mode and (price <= 0 or price >= 90000000)
        if not is_chaos_price:
            try:
                validated = ShoppingEvent(**event)
                return validated.model_dump()
            except Exception as e:
                print(f"[DQ] Validation failed: {e}")
                return None

        return event

    def _generate_campaign(self) -> dict:
        """Generate campaign info for promotional traffic."""
        campaigns = [
            {'id': 'camp_summer', 'name': '여름 세일'},
            {'id': 'camp_weekend', 'name': '주말 특가'},
            {'id': 'camp_member', 'name': '회원 전용'},
            {'id': 'camp_new', 'name': '신규 가입 혜택'},
            {'id': 'camp_holiday', 'name': '명절 이벤트'}
        ]
        return random.choice(campaigns)
