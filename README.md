# Triển khai Microservices Pipeline cho Bài toán Dự báo Tài chính Real-time

Mô tả
------
Dự án này thu thập giá Bitcoin từ API (CoinGecko), gửi dữ liệu vào Kafka, xử lý và tạo feature bằng một consumer, lưu dữ liệu (CSV / Parquet), và lưu feature vào Redis để một dịch vụ FastAPI sử dụng mô hình MLflow để dự đoán.

Thành phần chính
-----------------
- `docker-compose.yml`: khởi tạo Zookeeper, Kafka và Redis.
- `producer.py`: lấy giá từ CoinGecko và gửi message tới topic `btc_price` trên Kafka.
- `sink.py`: consumer phụ, ghi dữ liệu thô vào `data/data.csv`.
- `consumer.py`: consumer chính, gom nhóm bản ghi, lưu `data/data.parquet` và tạo feature (lag_1, lag_2, return) rồi lưu vào Redis key `btc_feature`.
- `app.py`: FastAPI service; nạp mô hình MLflow và phục vụ endpoint `/predict` (đọc feature từ Redis và trả về dự đoán).
- `monitor.py`: script giám sát, in ra giá trị `last_prediction` và `btc_feature` từ Redis (dùng để debug/demo).
- `requirements.txt`: danh sách thư viện Python cần cài.

Yêu cầu
-------
- Docker & Docker Compose
- Python 3.8+
- Kết nối Internet cho `producer.py` (để gọi API CoinGecko)

Cài đặt & Chạy nhanh
---------------------
1. Khởi động các dịch vụ cơ sở (Kafka + Zookeeper + Redis):

```bash
cd prj
docker-compose up -d
```

1. Tạo file môi trường `.env`. Ví dụ:

```env
DATABRICKS_HOST=<YOUR_DATABRICKS_HOST>
DATABRICKS_TOKEN=<YOUR_DATABRICKS_TOKEN>
```

3. Cài dependencies Python:

```bash
python -m pip install -r requirements.txt
```

1. Chạy từng thành phần (mở nhiều terminal):

- Producer (gửi giá BTC vào Kafka):

```bash
python producer.py
```

- Sink (ghi CSV phụ trợ, tùy chọn):

```bash
python sink.py
```

- Consumer chính (tạo feature và lưu xuống parquet, cập nhật Redis):

```bash
python consumer.py
```

- API phục vụ dự đoán (FastAPI):

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

- Monitor (xem Redis key):

```bash
python monitor.py
```

5. Kiểm tra endpoint dự đoán:

```bash
curl http://localhost:8000/predict
``

