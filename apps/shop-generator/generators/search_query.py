"""
Search Query Generator (Unstructured Data)

Generates realistic search queries with various patterns:
- Structured: "{brand} {item} {size}"
- Natural language: "엄마 생일선물 뭐가 좋을까"
- Typos and variations

Demonstrates handling of unstructured text data.
"""

import random
import uuid
from datetime import datetime
from faker import Faker

fake = Faker('ko_KR')


class SearchQueryGenerator:

    # Search patterns
    PATTERNS = {
        'structured': [
            "{brand} {item}",
            "{brand} {item} {size}",
            "{item} {color}",
            "{brand} {color} {item}",
        ],
        'recommendation': [
            "{item} 추천",
            "가성비 {item}",
            "{item} 추천 2024",
            "인기 {item}",
            "{item} 순위",
            "best {item}",
            "{item} 베스트",
        ],
        'natural': [
            "엄마 생일선물 뭐가 좋을까",
            "남친 선물 추천",
            "여친 선물 뭐가 좋아요",
            "20대 여자 선물",
            "30대 남자 선물",
            "집들이 선물 추천",
            "결혼 선물 뭐가 좋을까요",
            "졸업 선물 추천해주세요",
        ],
        'specific': [
            "{item} {price}원대",
            "{item} {price}원 이하",
            "{item} 무료배송",
            "{item} 당일배송",
            "{brand} 신상",
            "{brand} 세일",
            "{item} 할인",
        ],
        'comparison': [
            "{brand1} vs {brand2}",
            "{item} 뭐가 좋아요",
            "{brand} {item} 후기",
            "{item} 실사용 후기",
        ]
    }

    # Vocabulary
    BRANDS = {
        'fashion': ['나이키', '아디다스', '뉴발란스', '컨버스', '자라', '유니클로', 'H&M'],
        'electronics': ['삼성', '애플', 'LG', '소니', '샤오미', '로지텍', '레노버'],
        'beauty': ['이니스프리', '설화수', '라네즈', '맥', '에스티로더', '시세이도']
    }

    ITEMS = {
        'fashion': ['운동화', '청바지', '티셔츠', '원피스', '자켓', '가방', '백팩', '스니커즈'],
        'electronics': ['이어폰', '노트북', '태블릿', '마우스', '키보드', '모니터', '스피커'],
        'beauty': ['립스틱', '파운데이션', '쿠션', '마스크팩', '선크림', '스킨', '로션']
    }

    COLORS = ['흰색', '검정', '네이비', '베이지', '카키', '그레이', '블루', '레드', '핑크']

    SIZES = ['S', 'M', 'L', 'XL', '230', '240', '250', '260', '270', '280']

    PRICES = ['3만', '5만', '10만', '20만', '30만', '50만']

    # Typo patterns (to simulate real search behavior)
    TYPO_REPLACEMENTS = {
        'ㅋ': '',
        'ㅎ': '',
        '!!': '!',
        '??': '?',
    }

    def __init__(self):
        self.user_ids = [f"u_{uuid.uuid4().hex[:8]}" for _ in range(10000)]

    def generate(self) -> dict:
        """Generate a single search query event."""

        # Select pattern type
        pattern_type = random.choices(
            list(self.PATTERNS.keys()),
            weights=[0.35, 0.25, 0.15, 0.15, 0.10]
        )[0]

        # Generate query
        query = self._generate_query(pattern_type)

        # Add typos sometimes
        if random.random() < 0.1:  # 10% have typos
            query = self._add_typo(query)

        # Generate result info
        result_count = random.randint(0, 10000)
        clicked = random.random() < 0.7  # 70% click on something

        search_event = {
            'search_id': f"sq_{uuid.uuid4().hex}",
            'user_id': random.choice(self.user_ids),
            'query': query,
            'query_length': len(query),
            'pattern_type': pattern_type,
            'timestamp': datetime.now().isoformat(),
            'result_count': result_count,
            'clicked': clicked,
            'clicked_position': random.randint(1, 10) if clicked and result_count > 0 else None,
            'session_id': f"sess_{uuid.uuid4().hex[:12]}",
            'filters_applied': self._generate_filters() if random.random() < 0.3 else []
        }

        return search_event

    def _generate_query(self, pattern_type: str) -> str:
        """Generate query based on pattern type."""

        if pattern_type == 'natural':
            return random.choice(self.PATTERNS['natural'])

        pattern = random.choice(self.PATTERNS[pattern_type])

        # Select category
        category = random.choice(list(self.BRANDS.keys()))

        # Fill in placeholders
        replacements = {
            '{brand}': random.choice(self.BRANDS[category]),
            '{brand1}': random.choice(self.BRANDS[category]),
            '{brand2}': random.choice(self.BRANDS[category]),
            '{item}': random.choice(self.ITEMS[category]),
            '{color}': random.choice(self.COLORS),
            '{size}': random.choice(self.SIZES),
            '{price}': random.choice(self.PRICES),
        }

        query = pattern
        for key, value in replacements.items():
            query = query.replace(key, value)

        return query

    def _add_typo(self, query: str) -> str:
        """Add realistic typos to query."""

        typo_types = ['missing_char', 'duplicate', 'swap']
        typo_type = random.choice(typo_types)

        if len(query) < 3:
            return query

        if typo_type == 'missing_char':
            idx = random.randint(1, len(query) - 2)
            query = query[:idx] + query[idx+1:]
        elif typo_type == 'duplicate':
            idx = random.randint(0, len(query) - 1)
            query = query[:idx] + query[idx] + query[idx:]
        elif typo_type == 'swap':
            idx = random.randint(0, len(query) - 2)
            query = query[:idx] + query[idx+1] + query[idx] + query[idx+2:]

        return query

    def _generate_filters(self) -> list:
        """Generate applied search filters."""

        possible_filters = [
            {'type': 'price', 'min': 10000, 'max': 50000},
            {'type': 'price', 'min': 50000, 'max': 100000},
            {'type': 'brand', 'value': random.choice(['나이키', '아디다스', '삼성'])},
            {'type': 'category', 'value': random.choice(['fashion', 'electronics', 'beauty'])},
            {'type': 'delivery', 'value': 'free_shipping'},
            {'type': 'delivery', 'value': 'rocket_delivery'},
            {'type': 'rating', 'min': 4.0},
        ]

        return random.sample(possible_filters, k=random.randint(1, 3))
