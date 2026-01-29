"""
Review Text Generator (Unstructured Data)

Generates realistic Korean product reviews using templates and combinations.
This demonstrates handling of unstructured text data in the pipeline.
"""

import random
import uuid
from datetime import datetime, timedelta
from faker import Faker

fake = Faker('ko_KR')


class ReviewGenerator:

    # Review templates by aspect
    TEMPLATES = {
        'delivery': {
            'positive': [
                '배송이 정말 빨랐어요!',
                '배송 빠르고 좋아요',
                '다음날 바로 도착했어요',
                '배송이 생각보다 빨라서 좋았습니다',
                '배송 속도 최고예요'
            ],
            'neutral': [
                '배송은 보통이에요',
                '배송은 평범했어요',
                '배송 속도는 그냥 그래요'
            ],
            'negative': [
                '배송이 너무 늦었어요',
                '배송이 일주일이나 걸렸어요',
                '배송이 많이 지연됐네요',
                '배송 추적도 안 되고 너무 늦어요'
            ]
        },
        'quality': {
            'positive': [
                '품질이 정말 좋아요',
                '퀄리티 대만족입니다',
                '생각보다 품질이 훨씬 좋네요',
                '가격 대비 품질 최고예요',
                '품질 좋고 마음에 들어요'
            ],
            'neutral': [
                '품질은 가격만큼이에요',
                '품질 그냥 그래요',
                '기대한 만큼이에요'
            ],
            'negative': [
                '품질이 좀 별로예요',
                '사진이랑 많이 다르네요',
                '품질이 기대 이하예요',
                '싸구려 느낌이 나요'
            ]
        },
        'packaging': {
            'positive': [
                '포장이 꼼꼼해요',
                '포장 상태 완벽했어요',
                '선물용으로도 좋을 정도로 포장이 예뻐요'
            ],
            'neutral': [
                '포장은 기본이에요',
                '포장 상태는 보통이에요'
            ],
            'negative': [
                '포장이 좀 아쉬워요',
                '포장이 허술해서 걱정됐어요',
                '박스가 찌그러져서 왔어요'
            ]
        },
        'satisfaction': {
            'positive': [
                '재구매 의사 있어요!',
                '또 살 거예요',
                '강력 추천합니다',
                '만족스러워요',
                '잘 샀어요',
                '완전 대박이에요'
            ],
            'neutral': [
                '그냥 그래요',
                '보통이에요',
                '나쁘지 않아요'
            ],
            'negative': [
                '다신 안 살 것 같아요',
                '추천하기 어려워요',
                '실망이에요',
                '환불하고 싶어요'
            ]
        },
        'price': {
            'positive': [
                '가성비 최고예요',
                '이 가격에 이 정도면 대만족',
                '저렴하게 잘 샀어요'
            ],
            'neutral': [
                '가격은 그냥 그래요',
                '적당한 가격이에요'
            ],
            'negative': [
                '가격에 비해 별로예요',
                '너무 비싸요',
                '이 가격이면 좀...'
            ]
        }
    }

    # Additional random sentences
    RANDOM_COMMENTS = [
        '색상이 사진이랑 똑같아요',
        '사이즈가 딱 맞아요',
        '사이즈가 좀 작아요',
        '사이즈가 좀 커요',
        '어머니 선물로 샀는데 좋아하세요',
        '친구 추천으로 샀어요',
        '할인할 때 사면 좋을 것 같아요',
        '이 브랜드 팬이에요',
        '처음 구매인데 괜찮네요',
        '두 번째 구매예요',
        '색상이 예뻐요',
        '디자인이 마음에 들어요'
    ]

    def __init__(self):
        self.product_ids = [f"pd_{i:06d}" for i in range(1000)]
        self.user_ids = [f"u_{uuid.uuid4().hex[:8]}" for _ in range(10000)]

    def generate(self) -> dict:
        """Generate a single product review."""

        # Determine overall sentiment
        # Most reviews are positive (online shopping bias)
        sentiment_weights = [0.60, 0.25, 0.15]  # positive, neutral, negative
        overall_sentiment = random.choices(
            ['positive', 'neutral', 'negative'],
            weights=sentiment_weights
        )[0]

        # Generate rating based on sentiment
        if overall_sentiment == 'positive':
            rating = random.choices([5, 4], weights=[0.6, 0.4])[0]
        elif overall_sentiment == 'neutral':
            rating = random.choices([3, 4], weights=[0.7, 0.3])[0]
        else:
            rating = random.choices([1, 2], weights=[0.3, 0.7])[0]

        # Build review text
        review_text = self._build_review_text(overall_sentiment)

        # Generate timestamps
        created_at = datetime.now() - timedelta(
            days=random.randint(0, 30),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )

        # Generate images (some reviews have images)
        images = []
        if random.random() < 0.3:  # 30% have images
            num_images = random.randint(1, 5)
            images = [f"img_{uuid.uuid4().hex[:8]}.jpg" for _ in range(num_images)]

        review = {
            'review_id': f"rv_{uuid.uuid4().hex}",
            'product_id': random.choice(self.product_ids),
            'user_id': random.choice(self.user_ids),
            'rating': rating,
            'text': review_text,
            'images': images,
            'helpful_count': random.randint(0, 100) if random.random() < 0.5 else 0,
            'created_at': created_at.isoformat(),
            'verified_purchase': random.random() < 0.85  # 85% are verified
        }

        return review

    def _build_review_text(self, overall_sentiment: str) -> str:
        """Build review text by combining templates."""

        parts = []

        # Select which aspects to include (2-4 aspects)
        aspects = random.sample(
            list(self.TEMPLATES.keys()),
            k=random.randint(2, 4)
        )

        for aspect in aspects:
            # For each aspect, use sentiment with some variation
            if overall_sentiment == 'positive':
                sentiment = random.choices(
                    ['positive', 'neutral', 'negative'],
                    weights=[0.8, 0.15, 0.05]
                )[0]
            elif overall_sentiment == 'neutral':
                sentiment = random.choices(
                    ['positive', 'neutral', 'negative'],
                    weights=[0.3, 0.5, 0.2]
                )[0]
            else:
                sentiment = random.choices(
                    ['positive', 'neutral', 'negative'],
                    weights=[0.1, 0.2, 0.7]
                )[0]

            template = random.choice(self.TEMPLATES[aspect][sentiment])
            parts.append(template)

        # Add random comment sometimes
        if random.random() < 0.4:
            parts.append(random.choice(self.RANDOM_COMMENTS))

        # Shuffle for natural variation
        random.shuffle(parts)

        return ' '.join(parts)
