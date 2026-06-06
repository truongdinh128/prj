import csv
import json
import os
from pathlib import Path

import redis
from kafka import KafkaConsumer


BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
INPUT_TOPIC = os.getenv("KAFKA_TOPIC", "btc_price")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
OFFLINE_STORE = Path(os.getenv("OFFLINE_STORE", "data/raw.csv"))


r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
consumer = KafkaConsumer(
    INPUT_TOPIC,
    bootstrap_servers=BOOTSTRAP_SERVERS,
    group_id="raw-sink",
    auto_offset_reset="earliest",
    value_deserializer=lambda message: json.loads(message.decode("utf-8")),
)


def append_row(row: dict) -> None:
    OFFLINE_STORE.parent.mkdir(parents=True, exist_ok=True)
    file_exists = OFFLINE_STORE.exists()

    with OFFLINE_STORE.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["timestamp", "price", "source", "symbol"])
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def main() -> None:
    for message in consumer:
        payload = message.value
        row = {
            "timestamp": int(payload.get("timestamp", 0)),
            "price": float(payload["price"]),
            "source": payload.get("source", "coingecko"),
            "symbol": payload.get("symbol", "BTC"),
        }
        append_row(row)
        r.set("last_actual_price", json.dumps({"price": row["price"], "timestamp": row["timestamp"]}))
        print(f"Raw row stored: {row}")


if __name__ == "__main__":
    main()