"""
Configuration management for Data Generator.
Uses Pydantic for validation and environment variable loading.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_RETRIES: int = 5
    KAFKA_RETRY_INTERVAL: int = 2

    # Application Mode
    MODE: str = "normal"  # normal, sale, test
    LOG_LEVEL: str = "INFO"
    BASE_TPS: int = 100  # Base transactions per second

    # Host Info (injected from docker-compose)
    HOST_IP: str = "localhost"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
