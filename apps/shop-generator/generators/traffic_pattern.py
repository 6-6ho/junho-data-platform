"""
Traffic Pattern Controller

Controls traffic patterns based on time of day and special events.
Simulates realistic e-commerce traffic patterns:
- Peak hours: Lunch (12-14) and Evening (20-22)
- Low traffic: Late night (0-6)
- Sale events: 10x normal traffic
"""

import random
from datetime import datetime


class TrafficPatternController:

    # Hourly traffic pattern (multiplier)
    # Based on typical Korean e-commerce traffic patterns
    HOURLY_PATTERN = {
        0: 0.10,   # 새벽 0시
        1: 0.08,
        2: 0.05,
        3: 0.03,
        4: 0.03,
        5: 0.05,
        6: 0.15,   # 기상 시작
        7: 0.25,
        8: 0.35,   # 출근 시간
        9: 0.45,
        10: 0.55,
        11: 0.70,
        12: 0.85,  # 점심 피크
        13: 0.80,
        14: 0.65,
        15: 0.55,
        16: 0.50,
        17: 0.55,
        18: 0.65,  # 퇴근 시간
        19: 0.80,
        20: 1.00,  # 저녁 피크 (최대)
        21: 0.95,
        22: 0.80,
        23: 0.50,
    }

    # Day of week pattern (Monday=0, Sunday=6)
    DAILY_PATTERN = {
        0: 0.90,  # 월요일
        1: 0.95,  # 화요일
        2: 1.00,  # 수요일
        3: 1.00,  # 목요일
        4: 1.05,  # 금요일
        5: 1.20,  # 토요일 (주말 쇼핑)
        6: 1.15,  # 일요일
    }

    # Event type probabilities
    EVENT_TYPE_WEIGHTS = {
        'shopping': 0.50,  # 일반 쇼핑 이벤트
        'search': 0.25,    # 검색
        'review': 0.10,    # 리뷰
        'session': 0.15,   # 세션 (복합)
    }

    # Mode multipliers
    MODE_MULTIPLIERS = {
        'normal': 1.0,
        'sale': 10.0,      # 세일 기간
        'test': 0.1,       # 테스트 (적은 트래픽)
    }

    def __init__(self):
        self.current_mode = 'normal'

    def get_current_multiplier(self, mode: str = 'normal') -> float:
        """
        Get current traffic multiplier based on time and mode.

        Returns:
            float: Traffic multiplier (0.0 - 10.0+)
        """
        now = datetime.now()

        # Get hourly pattern
        hour = now.hour
        hourly_mult = self.HOURLY_PATTERN.get(hour, 0.5)

        # Get daily pattern
        day = now.weekday()
        daily_mult = self.DAILY_PATTERN.get(day, 1.0)

        # Get mode multiplier
        mode_mult = self.MODE_MULTIPLIERS.get(mode, 1.0)

        # Add some randomness (±20%)
        randomness = random.uniform(0.8, 1.2)

        # Calculate final multiplier
        final_mult = hourly_mult * daily_mult * mode_mult * randomness

        return final_mult

    def get_random_event_type(self) -> str:
        """
        Get random event type based on weights.

        Returns:
            str: Event type ('shopping', 'search', 'review', 'session')
        """
        types = list(self.EVENT_TYPE_WEIGHTS.keys())
        weights = list(self.EVENT_TYPE_WEIGHTS.values())

        return random.choices(types, weights=weights)[0]

    def should_generate_burst(self) -> bool:
        """
        Determine if we should generate a traffic burst.
        Simulates flash sales, viral products, etc.

        Returns:
            bool: True if burst should occur
        """
        # 1% chance of burst per second
        return random.random() < 0.01

    def get_burst_multiplier(self) -> float:
        """
        Get multiplier for traffic burst.

        Returns:
            float: Burst multiplier (2.0 - 5.0)
        """
        return random.uniform(2.0, 5.0)

    def simulate_time(self, hour: int, day: int = None) -> float:
        """
        Simulate traffic for a specific time (for testing/demo).

        Args:
            hour: Hour (0-23)
            day: Day of week (0=Monday, 6=Sunday)

        Returns:
            float: Traffic multiplier
        """
        hourly_mult = self.HOURLY_PATTERN.get(hour, 0.5)
        daily_mult = self.DAILY_PATTERN.get(day, 1.0) if day is not None else 1.0

        return hourly_mult * daily_mult

    def get_traffic_schedule(self) -> dict:
        """
        Get full 24-hour traffic schedule.

        Returns:
            dict: Hour -> multiplier mapping
        """
        return self.HOURLY_PATTERN.copy()

    def get_weekly_schedule(self) -> list:
        """
        Get weekly traffic pattern.

        Returns:
            list: 7*24 multipliers for each hour of the week
        """
        schedule = []
        for day in range(7):
            for hour in range(24):
                mult = self.HOURLY_PATTERN[hour] * self.DAILY_PATTERN[day]
                schedule.append({
                    'day': day,
                    'hour': hour,
                    'multiplier': mult
                })
        return schedule
