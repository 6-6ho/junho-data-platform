"""
Session Event Generator (Nested JSON - Unstructured Data)

Generates complex nested JSON structures representing user sessions.
Each session contains multiple events, device info, and context.

Demonstrates handling of deeply nested unstructured data in the pipeline.
"""

import random
import uuid
from datetime import datetime, timedelta
from faker import Faker

fake = Faker('ko_KR')


class SessionEventGenerator:

    EVENT_TYPES = ['search', 'view', 'add_cart', 'remove_cart', 'purchase', 'review', 'wishlist']

    DEVICE_TYPES = ['mobile', 'desktop', 'tablet']

    OS_MAP = {
        'mobile': ['iOS', 'Android'],
        'desktop': ['Windows', 'macOS', 'Linux'],
        'tablet': ['iOS', 'Android', 'Windows']
    }

    REFERRERS = ['direct', 'google', 'naver', 'instagram', 'facebook', 'youtube', 'tiktok', 'email', 'push_notification']

    PAGE_TYPES = ['home', 'category', 'search_results', 'product_detail', 'cart', 'checkout', 'order_complete', 'my_page']

    def __init__(self):
        self.user_ids = [f"u_{uuid.uuid4().hex[:8]}" for _ in range(10000)]
        self.product_ids = [f"pd_{i:06d}" for i in range(1000)]

    def generate(self) -> dict:
        """Generate a complete session event with nested structure."""

        session_id = f"sess_{uuid.uuid4().hex}"
        user_id = random.choice(self.user_ids)

        # Generate session duration (1 minute to 1 hour)
        session_duration = random.randint(60, 3600)
        session_start = datetime.now() - timedelta(seconds=session_duration)

        # Generate events within session
        num_events = random.randint(3, 20)
        events = self._generate_session_events(num_events, session_start, session_duration)

        # Generate device info
        device = self._generate_device_info()

        # Generate context
        context = self._generate_context()

        # Generate user agent string (unstructured)
        user_agent = self._generate_user_agent(device)

        session = {
            'session_id': session_id,
            'user_id': user_id,
            'started_at': session_start.isoformat(),
            'ended_at': (session_start + timedelta(seconds=session_duration)).isoformat(),
            'duration_seconds': session_duration,
            'event_count': len(events),
            'device': device,
            'context': context,
            'user_agent': user_agent,
            'events': events,
            'summary': self._generate_session_summary(events),
            'metadata': {
                'sdk_version': f"{random.randint(1,3)}.{random.randint(0,9)}.{random.randint(0,9)}",
                'app_build': random.randint(1000, 9999),
                'experiment_groups': self._generate_experiment_groups()
            }
        }

        return session

    def _generate_session_events(self, num_events: int, start_time: datetime, duration: int) -> list:
        """Generate events within a session."""

        events = []
        current_time = start_time
        time_per_event = duration // num_events

        # Start with common flow patterns
        flow_patterns = [
            ['search', 'view', 'view', 'add_cart'],
            ['view', 'view', 'add_cart', 'purchase'],
            ['search', 'view', 'add_cart', 'remove_cart', 'view', 'add_cart'],
            ['view', 'wishlist', 'view', 'add_cart'],
        ]

        for i in range(num_events):
            event_type = random.choice(self.EVENT_TYPES)

            event = {
                'event_index': i,
                'event_type': event_type,
                'timestamp': current_time.isoformat(),
                'page': random.choice(self.PAGE_TYPES),
                'duration_on_page': random.randint(5, 300)
            }

            # Add event-specific fields
            if event_type in ['view', 'add_cart', 'remove_cart', 'purchase', 'wishlist']:
                event['product'] = {
                    'product_id': random.choice(self.product_ids),
                    'category': random.choice(['fashion', 'electronics', 'beauty', 'food', 'home']),
                    'price': random.randint(10000, 500000),
                    'quantity': random.randint(1, 5) if event_type in ['add_cart', 'purchase'] else 1
                }

            if event_type == 'search':
                event['search'] = {
                    'query': self._generate_simple_query(),
                    'result_count': random.randint(0, 5000),
                    'filters': random.choice([[], ['price'], ['brand'], ['category', 'price']])
                }

            if event_type == 'purchase':
                event['transaction'] = {
                    'transaction_id': f"tx_{uuid.uuid4().hex[:12]}",
                    'payment_method': random.choice(['card', 'kakao_pay', 'naver_pay', 'toss']),
                    'total_amount': random.randint(10000, 1000000),
                    'discount_amount': random.randint(0, 50000),
                    'coupon_used': random.random() < 0.3
                }

            events.append(event)
            current_time += timedelta(seconds=time_per_event + random.randint(-10, 10))

        return events

    def _generate_device_info(self) -> dict:
        """Generate detailed device information."""

        device_type = random.choices(
            self.DEVICE_TYPES,
            weights=[0.65, 0.30, 0.05]
        )[0]

        os = random.choice(self.OS_MAP[device_type])

        device = {
            'type': device_type,
            'os': os,
            'os_version': f"{random.randint(10, 17)}.{random.randint(0, 5)}",
            'app_version': f"{random.randint(1,5)}.{random.randint(0,9)}.{random.randint(0,9)}",
            'screen': {
                'width': random.choice([375, 390, 414, 428, 1280, 1920, 2560]),
                'height': random.choice([667, 844, 896, 926, 720, 1080, 1440]),
                'density': random.choice([2, 3, 1, 1.5])
            },
            'network': {
                'type': random.choice(['wifi', '4g', '5g', '3g']),
                'carrier': random.choice(['SKT', 'KT', 'LGU+', None])
            },
            'is_tablet': device_type == 'tablet',
            'is_mobile': device_type == 'mobile',
            'locale': 'ko_KR',
            'timezone': 'Asia/Seoul'
        }

        # Add manufacturer for mobile/tablet
        if device_type in ['mobile', 'tablet']:
            if os == 'iOS':
                device['manufacturer'] = 'Apple'
                device['model'] = random.choice(['iPhone 13', 'iPhone 14', 'iPhone 15', 'iPad Pro', 'iPad Air'])
            else:
                device['manufacturer'] = random.choice(['Samsung', 'LG', 'Xiaomi'])
                device['model'] = random.choice(['Galaxy S23', 'Galaxy S24', 'Galaxy Tab S9'])

        return device

    def _generate_context(self) -> dict:
        """Generate session context."""

        context = {
            'referrer': random.choice(self.REFERRERS),
            'landing_page': random.choice(['/', '/event/summer-sale', '/category/fashion', '/product/pd_000001']),
            'utm': self._generate_utm() if random.random() < 0.4 else None,
            'campaign': self._generate_campaign() if random.random() < 0.3 else None,
            'is_first_visit': random.random() < 0.2,
            'previous_sessions_count': random.randint(0, 100),
            'days_since_last_visit': random.randint(0, 30) if random.random() > 0.2 else None,
            'location': {
                'country': 'KR',
                'region': random.choice(['서울', '경기', '부산', '대구', '인천', '광주', '대전']),
                'city': fake.city()
            }
        }

        return context

    def _generate_utm(self) -> dict:
        """Generate UTM parameters."""

        return {
            'source': random.choice(['google', 'facebook', 'instagram', 'naver', 'kakao']),
            'medium': random.choice(['cpc', 'cpm', 'social', 'email', 'display']),
            'campaign': random.choice(['summer_sale', 'new_arrival', 'retargeting', 'brand_awareness']),
            'term': random.choice(['운동화', '노트북', '원피스', None]),
            'content': random.choice(['banner_a', 'banner_b', 'video_ad', None])
        }

    def _generate_campaign(self) -> dict:
        """Generate campaign information."""

        campaigns = [
            {'id': 'camp_summer', 'name': '여름 세일', 'discount_rate': 0.2},
            {'id': 'camp_weekend', 'name': '주말 특가', 'discount_rate': 0.15},
            {'id': 'camp_member', 'name': '회원 전용', 'discount_rate': 0.1},
            {'id': 'camp_flash', 'name': '플래시 세일', 'discount_rate': 0.3},
        ]
        return random.choice(campaigns)

    def _generate_user_agent(self, device: dict) -> str:
        """Generate realistic user agent string."""

        if device['type'] == 'mobile':
            if device['os'] == 'iOS':
                return f"Mozilla/5.0 (iPhone; CPU iPhone OS {device['os_version'].replace('.', '_')} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
            else:
                return f"Mozilla/5.0 (Linux; Android {device['os_version']}; {device.get('model', 'SM-G991B')}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        else:
            if device['os'] == 'Windows':
                return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            else:
                return f"Mozilla/5.0 (Macintosh; Intel Mac OS X {device['os_version'].replace('.', '_')}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def _generate_simple_query(self) -> str:
        """Generate simple search query."""

        queries = [
            '나이키 운동화', '삼성 이어폰', '원피스 추천', '노트북 가성비',
            '여름 티셔츠', '청바지 세일', '무선 마우스', '애플 워치',
            '가방 신상', '화장품 세트'
        ]
        return random.choice(queries)

    def _generate_session_summary(self, events: list) -> dict:
        """Generate session summary statistics."""

        event_types = [e['event_type'] for e in events]

        summary = {
            'total_events': len(events),
            'unique_products_viewed': len(set(
                e.get('product', {}).get('product_id')
                for e in events
                if e.get('product')
            )),
            'searches_count': event_types.count('search'),
            'views_count': event_types.count('view'),
            'add_cart_count': event_types.count('add_cart'),
            'purchase_count': event_types.count('purchase'),
            'converted': 'purchase' in event_types,
            'bounce': len(events) == 1
        }

        return summary

    def _generate_experiment_groups(self) -> list:
        """Generate A/B test experiment groups."""

        experiments = [
            {'experiment_id': 'exp_checkout_v2', 'variant': random.choice(['control', 'treatment_a', 'treatment_b'])},
            {'experiment_id': 'exp_recommendation', 'variant': random.choice(['control', 'ml_v1', 'ml_v2'])},
            {'experiment_id': 'exp_search_ranking', 'variant': random.choice(['control', 'new_algo'])},
        ]

        return random.sample(experiments, k=random.randint(0, 2))
