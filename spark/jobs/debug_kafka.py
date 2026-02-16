from kafka import KafkaConsumer
import os
import json

bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
topic = "raw.ticker.usdtm"

print(f"Connecting to {bootstrap}, topic {topic}...")

consumer = KafkaConsumer(
    topic,
    bootstrap_servers=bootstrap,
    auto_offset_reset='earliest',
    enable_auto_commit=False,
    group_id='debug-group-1',
    value_deserializer=lambda x: x.decode('utf-8')
)

print("Consumer created. Polling...")

for message in consumer:
    print(f"Received: {message.value[:100]}...")
    break
