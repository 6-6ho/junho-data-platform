import threading
import json
import logging
import time
from datetime import datetime
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

logger = logging.getLogger(__name__)

class ConfigConsumerThread(threading.Thread):
    def __init__(self, settings, traffic_controller, shopping_gen):
        super().__init__(daemon=True)
        self.settings = settings
        self.traffic_controller = traffic_controller
        self.shopping_gen = shopping_gen
        self.running = True

    def run(self):
        consumer = None
        while self.running and not consumer:
            try:
                consumer = KafkaConsumer(
                    'generator-control',
                    bootstrap_servers=self.settings.KAFKA_BOOTSTRAP_SERVERS,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
                    auto_offset_reset='latest',
                    enable_auto_commit=True,
                    group_id='shop-generator-admin-group'
                )
                logger.info("✅ Successfully connected to generator-control Kafka topic.")
            except NoBrokersAvailable:
                logger.warning("Kafka not available for control topic. Retrying in 5 seconds...")
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error connecting to config topic: {e}")
                time.sleep(5)

        if not consumer: return

        while self.running:
            try:
                messages = consumer.poll(timeout_ms=1000)
                for tp, batch in messages.items():
                    for record in batch:
                        if record.value and getattr(record.value, 'get', None):
                            if record.value.get("type") == "UPDATE_SETTINGS":
                                new_config = record.value.get("settings", {})
                                logger.info(f"🚨 Received Admin Config Override: {new_config}")
                                
                                # Apply global modes
                                if 'mode' in new_config:
                                    self.settings.MODE = new_config['mode']
                                if 'base_tps' in new_config:
                                    self.settings.BASE_TPS = new_config['base_tps']
                                if 'chaos_mode' in new_config:
                                    self.settings.CHAOS_MODE = new_config['chaos_mode']
                                    self.shopping_gen.chaos_mode = new_config['chaos_mode']
                                
                                # Apply biases
                                self.shopping_gen.category_bias = new_config.get('category_bias')
                                self.shopping_gen.persona_bias = new_config.get('user_persona_bias')
                                
                                # Apply Expiration
                                expires_str = new_config.get('expires_at')
                                if expires_str:
                                    self.settings.EXPIRES_AT = datetime.fromisoformat(expires_str)
                                else:
                                    self.settings.EXPIRES_AT = None
            except Exception as e:
                logger.error(f"Error reading config: {e}")
                time.sleep(1)

    def stop(self):
        self.running = False
