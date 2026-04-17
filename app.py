import mlflow.pyfunc
import pandas as pd
from fastapi import FastAPI
from dotenv import load_dotenv
import redis
import json

# Nạp biến môi trường từ file .env
load_dotenv()

app = FastAPI()

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# MLflow sẽ tự đọc DATABRICKS_HOST và DATABRICKS_TOKEN từ os.environ
mlflow.set_tracking_uri("databricks")

# Load mô hình
model_name = "workspace.default.btc_model"
model_version = "1"
model = mlflow.pyfunc.load_model(f"models:/{model_name}/{model_version}")

@app.get("/predict")
def predict():
    data = r.get("btc_feature")

    if data is None:
        return {"error": "no data"}

    feature = json.loads(data)

    df = pd.DataFrame([feature]).astype('float64')

    pred = model.predict(df)[0]

    return {
        "feature": feature,
        "prediction": float(pred)
    }