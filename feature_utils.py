import pandas as pd


FEATURE_COLUMNS = ["lag_1", "lag_2", "return", "rsi", "macd", "signal", "hist"]
MIN_HISTORY = 30


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return (100 - (100 / (1 + rs))).fillna(50.0)


def add_features(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    if "timestamp" in data.columns:
        data = data.sort_values("timestamp")

    data = data.reset_index(drop=True)
    prices = data["price"].astype("float64")

    data["lag_1"] = prices.shift(1)
    data["lag_2"] = prices.shift(2)
    data["return"] = prices.pct_change()
    data["rsi"] = _rsi(prices)

    macd_fast = prices.ewm(span=12, adjust=False).mean()
    macd_slow = prices.ewm(span=26, adjust=False).mean()
    data["macd"] = macd_fast - macd_slow
    data["signal"] = data["macd"].ewm(span=9, adjust=False).mean()
    data["hist"] = data["macd"] - data["signal"]

    return data


def build_feature_payload(prices, timestamp: int):
    if len(prices) < MIN_HISTORY:
        return None

    data = add_features(pd.DataFrame({"price": list(prices)})).dropna()
    if data.empty:
        return None

    row = data.iloc[-1]
    payload = {column: float(row[column]) for column in FEATURE_COLUMNS}
    payload["price"] = float(row["price"])
    payload["timestamp"] = int(timestamp)
    return payload