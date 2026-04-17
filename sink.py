from kafka import KafkaConsumer
import json
import pandas as pd
import time
import os

consumer = KafkaConsumer(
    'btc_price',
    bootstrap_servers='localhost:9092',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

file_path = "data/data.csv"
os.makedirs("data", exist_ok=True)

rows = []

for msg in consumer:
    price = msg.value["price"]
    rows.append({
        "price": price,
        "timestamp": int(time.time())
    })

    if len(rows) >= 5:
        df = pd.DataFrame(rows)

        if not os.path.exists(file_path):
            df.to_csv(file_path, index=False)
        else:
            df.to_csv(file_path, mode='a', header=False, index=False)

        rows = []