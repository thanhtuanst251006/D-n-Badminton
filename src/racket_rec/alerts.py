import os

import numpy as np
import pandas as pd


def detect_price_anomalies(
    history_df: pd.DataFrame, z_thresh: float = -1.8
) -> pd.DataFrame:
    """
    Phát hiện mức giá giảm bất thường dựa trên Z-score và Rolling Median.
    Kỳ vọng cột: ['model', 'date', 'price_vnd']
    """
    anomalies = []
    for model, group in history_df.groupby("model"):
        group = group.sort_values("date")
        prices = group["price_vnd"].values
        if len(prices) < 4:
            continue
        mean_p = np.mean(prices[:-1])
        std_p = np.std(prices[:-1]) or 1.0
        median_p = np.median(prices[:-1])
        latest_p = prices[-1]

        z_score = (latest_p - mean_p) / std_p
        drop_pct = round((median_p - latest_p) / median_p * 100, 1)

        if z_score <= z_thresh and drop_pct >= 8.0:
            anomalies.append(
                {
                    "model": model,
                    "latest_price": int(latest_p),
                    "rolling_median": int(median_p),
                    "drop_pct": drop_pct,
                    "z_score": round(z_score, 2),
                }
            )
    return pd.DataFrame(anomalies)


def send_telegram_alert(message: str) -> bool:
    """Gửi tin nhắn cảnh báo giảm giá qua Telegram Bot."""
    import requests

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print(f"[Telegram Dry-Run]: {message}")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)
    return resp.status_code == 200


def generate_demo_history(
    catalog: pd.DataFrame, end_date: str, periods: int = 14
) -> pd.DataFrame:
    """Build repeatable synthetic prices without changing NumPy global state."""
    rng = np.random.default_rng(42)
    dates = pd.date_range(end=end_date, periods=periods).strftime("%Y-%m-%d")
    rows = []
    for position, (_, racket) in enumerate(catalog.iterrows()):
        for day, date in enumerate(dates):
            factor = (
                0.82
                if position == 0 and day == periods - 1
                else rng.uniform(0.98, 1.02)
            )
            rows.append(
                {
                    "model": racket["model"],
                    "date": date,
                    "price_vnd": int(racket["price_vnd"] * factor),
                }
            )
    return pd.DataFrame(rows, columns=["model", "date", "price_vnd"])
