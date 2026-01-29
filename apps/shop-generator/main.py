#!/usr/bin/env python3
"""
E-commerce Shopping Data Generator

Generates shopping events, reviews, and search queries with realistic traffic patterns.
Sends data to Kafka topics for downstream processing.
"""

import sys
import json
import time
import signal
import argparse
import logging
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

from generators.shopping_event import ShoppingEventGenerator
from generators.review import ReviewGenerator
from generators.search_query import SearchQueryGenerator
from generators.session_event import SessionEventGenerator
from generators.traffic_pattern import TrafficPatternController
from config import get_settings
from metrics import MetricsCollector

# Initialize settings
settings = get_settings()

# Logging setup
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Topics
TOPIC_SHOPPING_EVENTS = 'shopping-events'
TOPIC_REVIEWS = 'reviews'
TOPIC_SEARCH_QUERIES = 'search-queries'
TOPIC_SESSION_EVENTS = 'session-events'

# Global flag for graceful shutdown
running = True


def signal_handler(signum, frame):
    global running
    logger.info("Shutdown signal received. Stopping...")
    running = False


def create_kafka_producer():
    """Create Kafka producer with retry logic."""
    for attempt in range(settings.KAFKA_RETRIES):
        try:
            producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3
            )
            logger.info(f"Connected to Kafka at {settings.KAFKA_BOOTSTRAP_SERVERS}")
            return producer
        except NoBrokersAvailable:
            logger.warning(f"Kafka not available. Retry {attempt + 1}/{settings.KAFKA_RETRIES} in {settings.KAFKA_RETRY_INTERVAL}s...")
            time.sleep(settings.KAFKA_RETRY_INTERVAL)

    logger.error("Failed to connect to Kafka after maximum retries")
    sys.exit(1)


def generate_and_send(producer, generators, traffic_controller, mode, metrics):
    """Main generation loop."""
    global running

    shopping_gen = generators['shopping']
    review_gen = generators['review']
    search_gen = generators['search']
    session_gen = generators['session']

    events_sent = 0
    start_time = time.time()

    while running:
        try:
            # Get current traffic multiplier
            multiplier = traffic_controller.get_current_multiplier(mode)
            metrics.set_multiplier(multiplier)

            # Calculate events per second based on traffic pattern
            base_eps = settings.BASE_TPS  # Base events per second
            current_eps = int(base_eps * multiplier)

            # Generate batch of events
            batch_size = max(1, current_eps // 10)  # Send every 100ms

            for _ in range(batch_size):
                # Generate different event types with weighted probability
                event_type = traffic_controller.get_random_event_type()
                
                try:
                    topic = None
                    key = None
                    event = None

                    if event_type == 'shopping':
                        event = shopping_gen.generate()
                        topic = TOPIC_SHOPPING_EVENTS
                        key = event['user_id']
                    elif event_type == 'review':
                        event = review_gen.generate()
                        topic = TOPIC_REVIEWS
                        key = event['product_id']
                    elif event_type == 'search':
                        event = search_gen.generate()
                        topic = TOPIC_SEARCH_QUERIES
                        key = event['user_id']
                    elif event_type == 'session':
                        event = session_gen.generate()
                        topic = TOPIC_SESSION_EVENTS
                        key = event['session_id']

                    if topic and event:
                        producer.send(topic, key=key, value=event)
                        metrics.increment_events(event_type, mode)
                        events_sent += 1

                except Exception as e:
                    logger.error(f"Error sending event {event_type}: {e}")
                    metrics.increment_errors(event_type)

            # Flush and log progress
            # producer.flush() # Flush less frequently for performance if needed, but safe here

            if events_sent % 1000 == 0:
                elapsed = time.time() - start_time
                eps = events_sent / elapsed if elapsed > 0 else 0
                logger.info(f"Events sent: {events_sent} | Rate: {eps:.1f}/s | Multiplier: {multiplier:.2f}x | Mode: {mode}")

            # Sleep to maintain rate
            time.sleep(0.1)

        except Exception as e:
            logger.error(f"Error generating events: {e}")
            time.sleep(1)

    logger.info(f"Generator stopped. Total events sent: {events_sent}")


def main():
    parser = argparse.ArgumentParser(description='E-commerce Data Generator')
    parser.add_argument('--mode', type=str, default=settings.MODE, choices=['normal', 'sale', 'test'],
                        help='Traffic mode: normal, sale (10x traffic), or test')
    parser.add_argument('--duration', type=int, default=0,
                        help='Duration in seconds (0 = run forever)')
    args = parser.parse_args()

    logger.info(f"Starting data generator in {args.mode} mode")

    # Initialize metrics
    metrics = MetricsCollector()

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create Kafka producer
    producer = create_kafka_producer()

    # Initialize generators
    generators = {
        'shopping': ShoppingEventGenerator(),
        'review': ReviewGenerator(),
        'search': SearchQueryGenerator(),
        'session': SessionEventGenerator()
    }

    traffic_controller = TrafficPatternController()

    # Start duration timer if specified
    if args.duration > 0:
        def stop_after_duration():
            global running
            time.sleep(args.duration)
            running = False

        import threading
        timer = threading.Thread(target=stop_after_duration)
        timer.daemon = True
        timer.start()

    try:
        generate_and_send(producer, generators, traffic_controller, args.mode, metrics)
    finally:
        producer.close()
        logger.info("Kafka producer closed")


if __name__ == '__main__':
    main()
