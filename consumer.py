import json
import os
from collections import deque

import redis
from kafka import KafkaConsumer, KafkaProducer

from feature_utils import build_feature_payload


BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
INPUT_TOPIC = os.getenv("KAFKA_TOPIC", "btc_price")
OUTPUT_TOPIC = os.getenv("PROCESSED_TOPIC", "btc_price_processed")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
PRICE_BUFFER_SIZE = int(os.getenv("PRICE_BUFFER_SIZE", "60"))


r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
consumer = KafkaConsumer(
    INPUT_TOPIC,
    bootstrap_servers=BOOTSTRAP_SERVERS,
    group_id="stream-processing",
    auto_offset_reset="earliest",
    value_deserializer=lambda message: json.loads(message.decode("utf-8")),
)
producer = KafkaProducer(
    bootstrap_servers=BOOTSTRAP_SERVERS,
    value_serializer=lambda value: json.dumps(value).encode("utf-8"),
)

prices = deque(maxlen=PRICE_BUFFER_SIZE)


def main() -> None:
    for message in consumer:
        payload = message.value
        price = float(payload["price"])
        timestamp = int(payload.get("timestamp", 0))

        prices.append(price)
        r.set(
            "last_actual_price",
            json.dumps({"price": price, "timestamp": timestamp}),
        )

        feature_payload = build_feature_payload(prices, timestamp)
        if feature_payload is None:
            continue

        r.set("btc_feature", json.dumps(feature_payload))
        producer.send(OUTPUT_TOPIC, feature_payload)
        producer.flush()
        print(f"Feature: {feature_payload}")


if __name__ == "__main__":
    main()