from dataclasses import dataclass

import pandas as pd

LEVEL_MAX_STIFFNESS = {
    "Mới chơi (Newbie)": 3.0,
    "Phong trào (Intermediate)": 4.2,
    "Nâng cao / Bán chuyên (Advanced)": 5.0,
}


@dataclass
class UserPrefs:
    attack_ratio: float  # 0.0 (Điều cầu/Phòng thủ) -> 1.0 (Chuyên công)
    level: str  # Trình độ người chơi
    budget_vnd: int | None  # Ngân sách tối đa
    wrist_injury: bool = False  # Có tiền sử đau cổ tay / khuỷu tay không


def ideal_vector(prefs: UserPrefs) -> dict[str, float]:
    """Chuyển phiếu hỏi người dùng thành vector thông số lý tưởng."""
    target_balance = 2.0 + 2.8 * prefs.attack_ratio

    base_stiff = {
        "Mới chơi (Newbie)": 2.2,
        "Phong trào (Intermediate)": 3.3,
        "Nâng cao / Bán chuyên (Advanced)": 4.3,
    }.get(prefs.level, 3.0)
    target_stiffness = min(
        LEVEL_MAX_STIFFNESS.get(prefs.level, 5.0), base_stiff + 0.5 * prefs.attack_ratio
    )

    target_weight = 83.0 if prefs.attack_ratio < 0.75 else 85.5

    if prefs.wrist_injury:
        target_weight = min(target_weight, 82.0)
        target_stiffness = min(target_stiffness, 2.8)
        target_balance = min(target_balance, 3.2)

    return {
        "weight_g": round(target_weight, 2),
        "balance_score": round(target_balance, 2),
        "stiffness_score": round(target_stiffness, 2),
    }


def filter_candidates(catalog: pd.DataFrame, prefs: UserPrefs) -> pd.DataFrame:
    """Apply the same eligibility rules for recommendations and evaluation."""
    df = catalog.copy()
    if "specs_complete" in df:
        df = df[df["specs_complete"].eq(True)]
        df = df.dropna(
            subset=["price_vnd", "weight_g", "balance_score", "stiffness_score"]
        )
        if "availability" in df:
            df = df[df["availability"] != "Shop ghi hết hàng"]
        if "price_kind" in df:
            df = df[df["price_kind"] != "from"]
    if prefs.budget_vnd is not None:
        df = df[df["price_vnd"] <= prefs.budget_vnd]
        if "price_max_vnd" in df:
            df = df[df["price_max_vnd"] <= prefs.budget_vnd]
    df = df[df["stiffness_score"] <= LEVEL_MAX_STIFFNESS.get(prefs.level, 5.0)]
    if prefs.wrist_injury:
        df = df[(df["weight_g"] <= 84.0) & (df["stiffness_score"] <= 3.2)]
    return df


def recommend(
    catalog: pd.DataFrame,
    prefs: UserPrefs,
    k: int = 5,
    weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    """
    Bước 1: Lọc theo ràng buộc cứng (Ngân sách, Trình độ, Chấn thương cổ tay).
    Bước 2: Xếp hạng bằng độ tương đồng có trọng số & Giải thích mức đóng góp từng thông số.
    """
    if weights is None:
        weights = {"weight_g": 0.25, "balance_score": 0.45, "stiffness_score": 0.30}

    if k < 1:
        raise ValueError("k must be at least 1")
    df = filter_candidates(catalog, prefs)

    if df.empty:
        return df

    target = ideal_vector(prefs)
    features = ["weight_g", "balance_score", "stiffness_score"]
    ranges = {"weight_g": 20.0, "balance_score": 4.0, "stiffness_score": 4.0}

    scores = []
    explanations = []

    for _, row in df.iterrows():
        comp_sim = {}
        for f in features:
            diff = abs(row[f] - target[f]) / ranges[f]
            comp_sim[f] = max(0.0, 1.0 - diff)

        total_score = sum(comp_sim[f] * weights.get(f, 0.0) for f in features)
        total_weight = sum(weights.get(f, 0.0) for f in features) or 1.0
        final_pct = round((total_score / total_weight) * 100, 1)
        scores.append(final_pct)

        c_bal = round(comp_sim["balance_score"] * 100)
        c_stiff = round(comp_sim["stiffness_score"] * 100)
        c_weight = round(comp_sim["weight_g"] * 100)
        reason_str = (
            f"Đóng góp độ khớp: Điểm cân bằng {c_bal}% (mục tiêu {target['balance_score']}) | "
            f"Độ cứng {c_stiff}% (mục tiêu {target['stiffness_score']}) | "
            f"Trọng lượng {c_weight}% ({int(row['weight_g'])}g)."
        )
        if prefs.wrist_injury:
            reason_str += " [Đáp ứng giới hạn trọng lượng và độ cứng đã chọn]"
        explanations.append(reason_str)

    df["match_pct"] = scores
    df["reason"] = explanations
    return (
        df.sort_values(by=["match_pct", "price_vnd"], ascending=[False, True])
        .head(k)
        .reset_index(drop=True)
    )
