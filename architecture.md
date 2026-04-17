## Kiến trúc

### 1. Tổng thể

Hệ gồm 6 service tách biệt:

* ingestion
* stream processing
* feature store
* training
* serving
* monitoring

Giao tiếp qua Kafka + HTTP API

---

## 2. Luồng dữ liệu

### Real-time path

* Crypto WS/API → ingestion
* ingestion → Kafka
* stream processing consume Kafka
* tạo feature → lưu Redis (online feature)
* gọi model → predict
* trả kết quả → API / dashboard

---

### Batch path

* Kafka → lưu raw (PostgreSQL / Parquet)
* training service đọc data
* train model
* log vào MLflow
* push model mới

---

### Feedback loop

* monitoring đọc prediction + actual
* detect drift
* trigger training lại

---

## 3. Chi tiết từng service

### 1. Ingestion Service

* Input: Binance WS / CoinGecko
* Output: Kafka topic

Tech:

* Python async
* Apache Kafka

---

### 2. Stream Processing Service

* Consume Kafka
* Tính feature: RSI, MACD
* Gửi:

  * Redis (online)
  * Kafka (processed)

Tech:

* Python
* Redis

---

### 3. Feature Store

* Online: Redis
* Offline: PostgreSQL / file

Không cần tool phức tạp

---

### 4. Training Service

* Lấy data offline
* Train model (LSTM / regression)
* Log experiment
* Register model

Tech:

* MLflow
* Scheduler: cron / Apache Airflow (optional)

---

### 5. Serving Service

* API nhận request
* Lấy feature từ Redis
* Load model từ MLflow
* Trả prediction

Tech:

* FastAPI

---

### 6. Monitoring Service

* So sánh prediction vs actual
* Tính metric (RMSE, drift)
* Trigger retrain

Output:

* log
* alert

---

## 4. Kiến trúc logic

```
[Data Source]
      ↓
[Ingestion] → Kafka → [Stream Processing] → Redis
                          ↓
                       Predict
                          ↓
                      FastAPI
                          ↓
                      User/API

Kafka → Storage → Training → MLflow → Serving

Monitoring → Trigger Training
```
