import json
import os
from pathlib import Path

import joblib
import mlflow
import mlflow.pyfunc
import pandas as pd
import redis
from dotenv import load_dotenv
from fastapi import FastAPI

from feature_utils import FEATURE_COLUMNS


load_dotenv()

app = FastAPI()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
model_name = os.getenv("MODEL_NAME", "workspace.default.btc_model")
model_version = os.getenv("MODEL_VERSION", "1")
MODEL_FALLBACK_PATH = Path(os.getenv("MODEL_FALLBACK_PATH", "artifacts/btc_model.joblib"))
EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "/Shared/btc_model")

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def best_model_version() -> str:
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "databricks")
    try:
        mlflow.set_tracking_uri(tracking_uri)
        client = mlflow.tracking.MlflowClient()
        versions = client.search_model_versions(f"name='{model_name}'")
        best_version = model_version
        best_rmse = None

        for version in versions:
            run = client.get_run(version.run_id)
            rmse = run.data.metrics.get("rmse")
            if rmse is None:
                continue
            if best_rmse is None or rmse < best_rmse:
                best_rmse = rmse
                best_version = str(version.version)

        return best_version
    except Exception:
        return model_version


def load_model():
    try:
        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "databricks"))
        current_version = best_model_version()
        return mlflow.pyfunc.load_model(f"models:/{model_name}/{current_version}")
    except Exception:
        if MODEL_FALLBACK_PATH.exists():
            sklearn_model = joblib.load(MODEL_FALLBACK_PATH)

            class LocalModel:
                def predict(self, frame):
                    return sklearn_model.predict(frame)

            return LocalModel()
        return None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/predict")
def predict():
    data = r.get("btc_feature")
    if data is None:
        return {"error": "no feature data"}

    current_model = load_model()
    if current_model is None:
        return {"error": "model not available"}

    feature = json.loads(data)
    frame = pd.DataFrame([feature])[FEATURE_COLUMNS].astype("float64")
    prediction = float(current_model.predict(frame)[0])
    payload = {
        "feature": feature,
        "prediction": prediction,
        "timestamp": feature["timestamp"],
    }
    r.set("last_prediction", json.dumps(payload))
    return payload