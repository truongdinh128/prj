import json
import redis
from kafka import KafkaConsumer
import pandas as pd
import os

file_path = "./data/data.parquet"

rows = []

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

consumer = KafkaConsumer(
    'btc_price',
    bootstrap_servers='localhost:9092',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

prev = None
prev2 = None

for msg in consumer:
    price = msg.value["price"]

    rows.append({
    "price": price
    })

    if len(rows) >= 5:
        df = pd.DataFrame(rows)

        if os.path.exists(file_path):
            old = pd.read_parquet(file_path)
            df = pd.concat([old, df])

        df.to_parquet(file_path)
        rows = []

    if prev is not None and prev2 is not None:
        ret = (price - prev) / prev

        feature = {
            "lag_1": prev,
            "lag_2": prev2,
            "return": ret
        }

        r.set("btc_feature", json.dumps(feature))

        print("Feature:", feature)

    prev2 = prev
    prev = price