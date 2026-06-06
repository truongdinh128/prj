import json
import math
import os
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

from feature_utils import FEATURE_COLUMNS, add_features


DATA_PATH = Path(os.getenv("DATA_PATH", "data/raw.csv"))
MODEL_PATH = Path(os.getenv("MODEL_PATH", "artifacts/btc_model.joblib"))
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "databricks")
model_name = os.getenv("MODEL_NAME", "workspace.default.btc_model")
EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "/Shared/btc_model")


def load_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Missing data at {DATA_PATH}")

    frame = pd.read_csv(DATA_PATH)
    if frame.empty:
        raise ValueError("Training data is empty")

    data = add_features(frame).dropna().reset_index(drop=True)
    if len(data) < 10:
        raise ValueError("Not enough rows to train a model")

    return data


def train() -> dict:
    frame = load_data()
    split_index = max(int(len(frame) * 0.8), 1)
    train_frame = frame.iloc[:split_index]
    test_frame = frame.iloc[split_index:] if split_index < len(frame) else frame.iloc[-1:]

    model = LinearRegression()
    model.fit(train_frame[FEATURE_COLUMNS], train_frame["price"])

    predictions = model.predict(test_frame[FEATURE_COLUMNS])
    rmse = math.sqrt(mean_squared_error(test_frame["price"], predictions))

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    registered = False
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(EXPERIMENT_NAME)
        with mlflow.start_run():
            mlflow.log_param("rows", len(frame))
            mlflow.log_param("features", ",".join(FEATURE_COLUMNS))
            mlflow.log_metric("rmse", rmse)
            mlflow.sklearn.log_model(model, artifact_path="model", registered_model_name=model_name)
            registered = True
    except Exception:
        mlflow.set_tracking_uri("file:./mlruns")
        with mlflow.start_run():
            mlflow.log_param("rows", len(frame))
            mlflow.log_param("features", ",".join(FEATURE_COLUMNS))
            mlflow.log_metric("rmse", rmse)
            mlflow.sklearn.log_model(model, artifact_path="model")

    result = {
        "model_path": str(MODEL_PATH),
        "rmse": rmse,
        "rows": len(frame),
        "mlflow_tracking_uri": MLFLOW_TRACKING_URI,
        "registered": registered,
    }
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    train()