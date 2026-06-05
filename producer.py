import time
import json
import requests
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

url = "https://api.coingecko.com/api/v3/simple/price"

while True:
    try:
        response = requests.get(url, params={
            "ids": "bitcoin",
            "vs_currencies": "usd"
        })
        
        data = response.json()

        if "bitcoin" in data:
            price = data["bitcoin"]["usd"]
            producer.send("btc_price", {"price": price})
            print("Sent:", price)
        else:
            print("Error: API limit reached or invalid response.", data)

    except Exception as e:
        print("Network error:", e)

    time.sleep(15)