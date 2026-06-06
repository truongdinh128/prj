import json
import os
import time

import requests
from kafka import KafkaProducer


BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_NAME = os.getenv("KAFKA_TOPIC", "btc_price")
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "5"))
SOURCE_URL = os.getenv("PRICE_SOURCE_URL", "https://api.coingecko.com/api/v3/simple/price")


producer = KafkaProducer(
    bootstrap_servers=BOOTSTRAP_SERVERS,
    value_serializer=lambda value: json.dumps(value).encode("utf-8"),
)


def fetch_price() -> float:
    response = requests.get(
        SOURCE_URL,
        params={"ids": "bitcoin", "vs_currencies": "usd"},
        timeout=2,
    )
    response.raise_for_status()

    data = response.json()
    bitcoin = data.get("bitcoin")
    if not bitcoin or "usd" not in bitcoin:
        raise ValueError(f"Unexpected response: {data}")

    return float(bitcoin["usd"])


def main() -> None:
    while True:
        try:
            price = fetch_price()
            message = {
                "price": price,
                "timestamp": int(time.time()),
                "source": "coingecko",
                "symbol": "BTC",
            }
            producer.send(TOPIC_NAME, message)
            producer.flush()
            print(f"Sent: {price}")
        except Exception as error:
            print(f"Ingestion error: {error}")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()