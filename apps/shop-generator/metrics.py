"""
Metrics collection for Data Generator.
Exposes Prometheus-compatible metrics.
"""

from prometheus_client import Counter, Gauge, start_http_server
import logging

logger = logging.getLogger(__name__)

# Metrics
EVENTS_SENT = Counter('events_sent_total', 'Total number of events sent', ['type', 'mode'])
EVENTS_ERROR = Counter('events_error_total', 'Total number of failed events', ['type'])
CURRENT_MULTIPLIER = Gauge('traffic_multiplier', 'Current traffic multiplier')


class MetricsCollector:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MetricsCollector, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self, port=8000):
        if not self.initialized:
            try:
                start_http_server(port)
                logger.info(f"Metrics server started on port {port}")
            except Exception as e:
                logger.warning(f"Failed to start metrics server: {e}")
            self.initialized = True

    def increment_events(self, event_type: str, mode: str):
        EVENTS_SENT.labels(type=event_type, mode=mode).inc()

    def increment_errors(self, event_type: str):
        EVENTS_ERROR.labels(type=event_type).inc()

    def set_multiplier(self, value: float):
        CURRENT_MULTIPLIER.set(value)
