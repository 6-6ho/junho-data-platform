import os
import time
import json
import logging
import websocket
from kafka import KafkaProducer

# Config
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC_NAME = "raw.ticker.usdtm"
WS_URL = "wss://fstream.binance.com/stream?streams=!ticker@arr"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def get_producer():
    while True:
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            logger.info("Connected to Kafka")
            return producer
        except Exception as e:
            logger.warning(f"Failed to connect to Kafka: {e}. Retrying in 5s...")
            time.sleep(5)

producer = get_producer()

def on_message(ws, message):
    try:
        data = json.loads(message)
        # data format: {"stream": "...", "data": [ ...tickers... ]}
        if "data" in data:
            for t in data["data"]:
                # Normalization
                payload = {
                    "event_time_ms": t["E"],
                    "symbol": t["s"],
                    "price": float(t["c"]),
                    "volume_24h": float(t["v"]),
                    "quote_volume_24h": float(t["q"]),
                    "change_pct_24h": float(t["P"])
                }
                producer.send(TOPIC_NAME, key=t["s"].encode('utf-8'), value=payload)
    except Exception as e:
        logger.error(f"Error processing message: {e}")

def on_error(ws, error):
    logger.error(f"WebSocket Error: {error}")

def on_close(ws, close_status_code, close_msg):
    logger.info("WebSocket Closed")

def on_open(ws):
    logger.info("WebSocket Opened")

def run():
    while True:
        try:
            ws = websocket.WebSocketApp(
                WS_URL,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            ws.run_forever()
            time.sleep(5) # Cooldown before reconnect
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run()
