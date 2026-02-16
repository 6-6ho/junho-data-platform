"""
Shopping Event Generator

Generates realistic e-commerce shopping events:
- search: Product search
- view: Product detail view
- add_cart: Add to cart
- purchase: Complete purchase
"""

import random
import uuid
from datetime import datetime
from faker import Faker

fake = Faker('ko_KR')


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

    def __init__(self, chaos_mode: bool = False):
        self.chaos_mode = chaos_mode
        self.product_cache = self._generate_product_catalog()
        self.user_pool = [f"u_{uuid.uuid4().hex[:8]}" for _ in range(10000)]
        
        # Chaos Mode: 장애 상태 관리
        self.failed_categories = set()      # 장애 난 카테고리
        self.failed_payments = set()        # 장애 난 결제수단
        self._chaos_check_counter = 0       # 장애 상태 변경 주기 관리

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
        
        # Chaos Mode: 장애 상태 업데이트
        if self.chaos_mode:
            self._simulate_failures()

        # Select event type based on weights
        event_type = random.choices(self.EVENT_TYPES, weights=self.EVENT_WEIGHTS)[0]

        # Select product
        product = random.choice(self.product_cache)
        
        # Chaos Mode: 장애 난 카테고리면 데이터 누락!
        if self.chaos_mode and product['category'] in self.failed_categories:
            return None

        # Select user
        user_id = random.choice(self.user_pool)

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
            'session_id': f"sess_{uuid.uuid4().hex[:12]}",
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
