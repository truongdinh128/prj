import json
import math
import os
import subprocess
import sys
import time
from collections import deque

import redis
import requests


REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
SERVING_URL = os.getenv("SERVING_URL", "http://localhost:8000")
POLL_INTERVAL_SECONDS = int(os.getenv("MONITOR_INTERVAL_SECONDS", "10"))
ERROR_THRESHOLD = float(os.getenv("ERROR_THRESHOLD", "1000"))
DRIFT_THRESHOLD = float(os.getenv("DRIFT_THRESHOLD", "0.05"))
COOLDOWN_SECONDS = int(os.getenv("RETRAIN_COOLDOWN_SECONDS", "300"))


r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
error_window = deque(maxlen=20)
actual_window = deque(maxlen=20)
last_retrain_at = 0.0


def read_json(key: str):
    value = r.get(key)
    if not value:
        return None
    return json.loads(value)


def trigger_retrain() -> None:
    subprocess.run([sys.executable, "training.py"], check=False)


def detect_drift() -> bool:
    if len(actual_window) < 10 or len(error_window) < 5:
        return False

    recent_actuals = list(actual_window)[-5:]
    previous_actuals = list(actual_window)[:-5]
    if not previous_actuals:
        return False

    recent_mean = sum(recent_actuals) / len(recent_actuals)
    previous_mean = sum(previous_actuals) / len(previous_actuals)
    if previous_mean == 0:
        return False

    relative_shift = abs(recent_mean - previous_mean) / abs(previous_mean)
    rmse = math.sqrt(sum(error * error for error in error_window) / len(error_window))
    r.set("monitor:last_metric", json.dumps({"rmse": rmse, "drift": relative_shift}))
    return rmse > ERROR_THRESHOLD or relative_shift > DRIFT_THRESHOLD


def main() -> None:
    global last_retrain_at

    while True:
        try:
            response = requests.get(f"{SERVING_URL}/predict", timeout=10)
            if response.ok:
                response_payload = response.json()
                if "prediction" not in response_payload:
                    print(response_payload)
                    time.sleep(POLL_INTERVAL_SECONDS)
                    continue

                actual_payload = read_json("last_actual_price")
                if actual_payload:
                    prediction = float(response_payload["prediction"])
                    actual = float(actual_payload["price"])
                    error = abs(prediction - actual)

                    error_window.append(error)
                    actual_window.append(actual)

                    metric = {
                        "prediction": prediction,
                        "actual": actual,
                        "error": error,
                        "rmse": math.sqrt(sum(value * value for value in error_window) / len(error_window)),
                    }
                    print(metric)

                    now = time.time()
                    if now - last_retrain_at >= COOLDOWN_SECONDS and detect_drift():
                        last_retrain_at = now
                        trigger_retrain()
            else:
                print(f"Serving unavailable: {response.status_code}")
        except Exception as error:
            print(f"Monitoring error: {error}")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()