import re
from pathlib import Path

import pandas as pd


def clean_price(price_str):
    """Bóc tách cụm giá tiền đầu tiên, xử lý cả trường hợp số bị dính liền."""
    if pd.isna(price_str):
        return None
    s = str(price_str)
    matches = re.findall(r"\d{1,3}(?:[.,]\d{3})+", s)
    if matches:
        return int(re.sub(r"[^\d]", "", matches[0]))
    s_digits = re.sub(r"[^\d]", "", s)
    match_zeros = re.search(r"^(\d+?000)", s_digits)
    if match_zeros:
        return int(match_zeros.group(1))
    return int(s_digits) if s_digits else None


def clean_weight(w_str):
    """Chuẩn hóa trọng lượng 2U/3U/4U/5U/F hoặc số gram về số thực (gram)."""
    if pd.isna(w_str):
        return None
    s = str(w_str).upper()
    if "2U" in s:
        return 92.0
    if "3U" in s:
        return 88.0
    if "4U" in s:
        return 83.0
    if "5U" in s:
        return 78.0
    if "F" in s or "6U" in s:
        return 73.0
    m = re.search(r"(\d{2,3}(?:\.\d+)?)\s*G", s)
    if m:
        return float(m.group(1))
    return None


def clean_balance(b_str):
    """Chuẩn hóa điểm cân bằng về thang điểm 1.0 (Nhẹ đầu) -> 5.0 (Siêu nặng đầu)."""
    if pd.isna(b_str):
        return None
    s = str(b_str).lower()
    if "siêu nặng" in s or "rất nặng" in s:
        return 4.8
    if "hơi nặng" in s:
        return 3.6
    if "cân bằng" in s or "công thủ" in s:
        return 3.0
    if "nặng đầu" in s or "công" in s:
        return 4.3
    if "hơi nhẹ" in s:
        return 2.5
    if "nhẹ đầu" in s or "thủ" in s:
        return 2.0
    m = re.search(r"(\d{3})\s*mm", s)
    if m:
        mm = int(m.group(1))
        return round(min(5.0, max(1.0, (mm - 280) / 7.0)), 2)
    return None


def clean_stiffness(s_str):
    """Chuẩn hóa độ cứng đũa về thang điểm 1.0 (Siêu dẻo) -> 5.0 (Siêu cứng)."""
    if pd.isna(s_str):
        return None
    s = str(s_str).lower()
    if "siêu cứng" in s or "extra stiff" in s:
        return 5.0
    if "hơi cứng" in s:
        return 3.8
    if "trung bình" in s or "medium" in s:
        return 3.0
    if "cứng" in s or "stiff" in s:
        return 4.3
    if "hơi dẻo" in s:
        return 2.5
    if "dẻo" in s or "flexible" in s:
        return 2.0
    return None


def clean_rackets(df: pd.DataFrame) -> pd.DataFrame:
    """Pipeline làm sạch toàn diện kèm cột imputation_reason ghi rõ lý do điền khuyết."""
    out = df.copy()
    out["price_vnd"] = out["price_raw"].apply(clean_price)
    out["weight_g"] = out["weight_raw"].apply(clean_weight)
    out["balance_score"] = out["balance_raw"].apply(clean_balance)
    out["stiffness_score"] = out["stiffness_raw"].apply(clean_stiffness)

    reasons = []
    median_price = (
        out["price_vnd"].median() if out["price_vnd"].notna().any() else 1500000
    )

    for idx, row in out.iterrows():
        row_reasons = []
        if pd.isna(row["price_vnd"]):
            out.at[idx, "price_vnd"] = int(median_price)
            row_reasons.append("Thiếu giá -> Điền trung vị toàn tập")
        if pd.isna(row["weight_g"]):
            out.at[idx, "weight_g"] = 83.0
            row_reasons.append("Thiếu trọng lượng -> Mặc định 4U (83g phổ biến nhất)")
        if pd.isna(row["balance_score"]):
            out.at[idx, "balance_score"] = 3.0
            row_reasons.append("Thiếu điểm cân bằng -> Mặc định Cân bằng (3.0)")
        if pd.isna(row["stiffness_score"]):
            out.at[idx, "stiffness_score"] = 3.0
            row_reasons.append("Thiếu độ cứng -> Mặc định Trung bình (3.0)")

        reasons.append("; ".join(row_reasons) if row_reasons else "Đầy đủ thông số gốc")

    out["imputation_reason"] = reasons
    return out


if __name__ == "__main__":
    raw_df = pd.read_csv("data/raw/rackets_raw.csv")
    cleaned_df = clean_rackets(raw_df)
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    out_file = "data/processed/rackets_cleaned.csv"
    cleaned_df.to_csv(out_file, index=False, encoding="utf-8-sig")
    print(f"Đã làm sạch {len(cleaned_df)} dòng và lưu tại: {out_file}")
