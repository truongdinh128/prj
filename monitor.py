import redis
import time

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

while True:
    pred = r.get("last_prediction")
    feature = r.get("btc_feature")

    if pred and feature:
        print("Prediction:", pred)

    time.sleep(10)