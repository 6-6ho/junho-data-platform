"""
Flink SQL + Python Sink job for Trade Movers detection.

v3: SQL-based pipeline
  - Parsing, filtering, 1-min TUMBLE aggregation all run in JVM via Flink SQL
  - Python sink assembles 5m/10m sliding windows from 1-min bars
  - Beam gRPC overhead reduced from 5 calls/record to 1 call/1-min-bar

Data flow:
  Kafka(raw.ticker.usdtm)
    → [SQL: JSON parse + USDT filter + watermark]          — JVM
    → [SQL: TUMBLE(1m) + FIRST_VALUE/LAST_VALUE per symbol] — JVM
    → to_data_stream()  (~300 rows/min)
    → [Python Sink: 5m/10m sliding buffer + DB write + alert]
"""

import os
import sys
import time
from collections import defaultdict, deque
from datetime import datetime

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.checkpoint_storage import FileSystemCheckpointStorage
from pyflink.datastream.functions import MapFunction, RuntimeContext
from pyflink.table import StreamTableEnvironment

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.db import save_movers_batch, save_market_snapshot_flink, DBConnection
from common.alert import send_telegram_alert, AlertManager

# CONFIG
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

THRESHOLD_5M = 3.0
THRESHOLD_5M_ALERT = 5.0
THRESHOLD_10M = 7.0

MOVERS_COOLDOWN_5M = 300
MOVERS_COOLDOWN_10M = 600

am = AlertManager()


# ── Sink Functions ──────────────────────────────────────────────────────

class MoversSink5m(MapFunction):
    """Assembles 5m sliding window from 1-min bars.
    Keeps last 5 bars per symbol, computes open/close/change_pct."""

    def open(self, runtime_context: RuntimeContext):
        self._bars = defaultdict(lambda: deque(maxlen=5))
        self._cooldowns = {}
        self._snapshot_buf = []
        self._movers_buf = []
        self._last_flush = time.time()

    def _flush(self):
        try:
            if self._snapshot_buf:
                save_market_snapshot_flink(self._snapshot_buf)
                self._snapshot_buf = []
            if self._movers_buf:
                save_movers_batch(self._movers_buf)
                self._movers_buf = []
        except Exception as e:
            print(f"[Sink5m] DB flush error: {e}")
            try:
                DBConnection.close_all()
                DBConnection._pool = None
            except Exception:
                pass
        self._last_flush = time.time()

    def map(self, value):
        row = value
        symbol = str(row[1])
        open_1m = float(row[2])
        close_1m = float(row[3])
        volume_24h = float(row[4])
        change_pct_24h = float(row[5])
        event_time_str = str(row[0])

        # Append this 1-min bar
        self._bars[symbol].append({
            "open": open_1m, "close": close_1m,
            "volume_24h": volume_24h, "change_pct_24h": change_pct_24h,
            "event_time": event_time_str
        })

        bars = self._bars[symbol]
        if len(bars) < 2:
            return value

        # 5m window: open from oldest bar, close from newest
        open_price = bars[0]["open"]
        close_price = bars[-1]["close"]

        if open_price == 0:
            return value

        change_pct = ((close_price - open_price) / open_price) * 100

        # Buffer snapshot
        self._snapshot_buf.append({
            "symbol": symbol,
            "price": close_price,
            "change_pct_24h": change_pct_24h,
            "volume_24h": volume_24h,
            "change_pct_window": change_pct,
            "vol_ratio": 0.0,
            "event_time": event_time_str
        })

        # Check movers threshold
        status = None
        if change_pct >= THRESHOLD_5M_ALERT:
            status = "[Large] Rise"
        elif change_pct >= THRESHOLD_5M:
            status = "[Small] Rise"

        if status:
            now_ms = int(time.time() * 1000)
            last_ms = self._cooldowns.get(symbol, 0)
            if (now_ms - last_ms) / 1000 >= MOVERS_COOLDOWN_5M:
                self._cooldowns[symbol] = now_ms
                self._movers_buf.append({
                    "type": "rise", "symbol": symbol, "status": status,
                    "window": "5m", "event_time": event_time_str,
                    "change_pct_window": change_pct,
                    "change_pct_24h": change_pct_24h, "vol_ratio": 0.0
                })

                if "Large" in status and am.should_send(symbol):
                    try:
                        send_telegram_alert(
                            f"\U0001f680 *{status}: {symbol} (5m)*\n"
                            f"Price: *{close_price}*\n"
                            f"Change: *{change_pct:.2f}%*\n"
                            f"Time: {event_time_str}"
                        )
                        am.update(symbol)
                        print(f"[Alert] {symbol} +{change_pct:.1f}%")
                    except Exception:
                        pass

        if len(self._snapshot_buf) >= 100 or (time.time() - self._last_flush) > 2:
            self._flush()

        return value

    def close(self):
        self._flush()


class MoversSink10m(MapFunction):
    """Assembles 10m sliding window from 1-min bars. Movers only."""

    def open(self, runtime_context: RuntimeContext):
        self._bars = defaultdict(lambda: deque(maxlen=10))
        self._cooldowns = {}
        self._movers_buf = []
        self._last_flush = time.time()

    def _flush(self):
        try:
            if self._movers_buf:
                save_movers_batch(self._movers_buf)
                self._movers_buf = []
        except Exception as e:
            print(f"[Sink10m] DB flush error: {e}")
            try:
                DBConnection.close_all()
                DBConnection._pool = None
            except Exception:
                pass
        self._last_flush = time.time()

    def map(self, value):
        row = value
        symbol = str(row[1])
        open_1m = float(row[2])
        close_1m = float(row[3])
        change_pct_24h = float(row[5])
        event_time_str = str(row[0])

        self._bars[symbol].append({
            "open": open_1m, "close": close_1m,
            "change_pct_24h": change_pct_24h,
            "event_time": event_time_str
        })

        bars = self._bars[symbol]
        if len(bars) < 5:
            return value

        open_price = bars[0]["open"]
        close_price = bars[-1]["close"]

        if open_price == 0:
            return value

        change_pct = ((close_price - open_price) / open_price) * 100

        if change_pct < THRESHOLD_10M:
            return value

        status = "[Small] Rise"
        now_ms = int(time.time() * 1000)
        last_ms = self._cooldowns.get(symbol, 0)
        if (now_ms - last_ms) / 1000 < MOVERS_COOLDOWN_10M:
            return value

        self._cooldowns[symbol] = now_ms
        self._movers_buf.append({
            "type": "rise", "symbol": symbol, "status": status,
            "window": "10m", "event_time": event_time_str,
            "change_pct_window": change_pct,
            "change_pct_24h": change_pct_24h,
        })

        if am.should_send(symbol, cooldown_override=MOVERS_COOLDOWN_10M):
            try:
                send_telegram_alert(
                    f"\U0001f680 *{status}: {symbol} (10m)*\n"
                    f"Price: *{close_price}*\n"
                    f"Change: *{change_pct:.2f}%*\n"
                    f"Time: {event_time_str}"
                )
                am.update(symbol)
                print(f"[Alert] {symbol} +{change_pct:.1f}% (10m)")
            except Exception:
                pass

        if len(self._movers_buf) >= 10 or (time.time() - self._last_flush) > 2:
            self._flush()

        return value

    def close(self):
        self._flush()


# ── Main ────────────────────────────────────────────────────────────────

def run():
    print("Starting Flink Trade Movers SQL job v3...")

    # --- StreamExecutionEnvironment ---
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)
    env.enable_checkpointing(300000)  # 5 min
    env.get_checkpoint_config().set_checkpoint_storage(
        FileSystemCheckpointStorage("file:///opt/flink/checkpoints")
    )

    # --- JARs (must be added before TableEnvironment creation) ---
    env.add_jars(
        "file:///opt/flink/usrlib/flink-sql-connector-kafka-3.1.0-1.18.jar",
        "file:///opt/flink/usrlib/flink-json-1.18.1.jar"
    )

    # --- Table Environment ---
    t_env = StreamTableEnvironment.create(stream_execution_environment=env)

    # --- Kafka Source (SQL DDL) — runs entirely in JVM ---
    t_env.execute_sql(f"""
        CREATE TABLE raw_trades (
            event_time_ms BIGINT,
            symbol        STRING,
            price         DOUBLE,
            volume_24h    DOUBLE,
            change_pct_24h DOUBLE,
            event_time AS TO_TIMESTAMP_LTZ(event_time_ms, 3),
            WATERMARK FOR event_time AS event_time - INTERVAL '1' MINUTE
        ) WITH (
            'connector'                    = 'kafka',
            'topic'                        = 'raw.ticker.usdtm',
            'properties.bootstrap.servers' = '{KAFKA_BOOTSTRAP}',
            'properties.group.id'          = 'flink-trade-movers-sql',
            'scan.startup.mode'            = 'latest-offset',
            'format'                       = 'json',
            'json.ignore-parse-errors'     = 'true'
        )
    """)

    # --- 1-minute TUMBLE (JVM) — no merge needed, FIRST/LAST_VALUE work ---
    result_1m = t_env.sql_query("""
        SELECT
            window_end,
            symbol,
            FIRST_VALUE(price) AS open_price,
            LAST_VALUE(price)  AS close_price,
            LAST_VALUE(volume_24h) AS volume_24h,
            LAST_VALUE(change_pct_24h) AS change_pct_24h
        FROM TABLE(
            TUMBLE(TABLE raw_trades, DESCRIPTOR(event_time),
                   INTERVAL '1' MINUTE)
        )
        WHERE symbol LIKE '%USDT' AND POSITION('_' IN symbol) = 0
        GROUP BY window_start, window_end, symbol
    """)

    # --- Table → DataStream → Python Sinks ---
    ds_1m = t_env.to_data_stream(result_1m)

    # Both sinks receive 1-min bars; each assembles its own sliding window
    ds_1m.map(MoversSink5m())    # 5-bar buffer → 5m window
    ds_1m.map(MoversSink10m())   # 10-bar buffer → 10m window

    print("Executing Flink SQL job...")
    env.execute("TradeMovers-SQL")


if __name__ == "__main__":
    run()
