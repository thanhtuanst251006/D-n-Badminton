import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.tree import DecisionTreeClassifier

from racket_rec.recommender import UserPrefs, filter_candidates, ideal_vector, recommend


def get_ground_truth_survey():
    """15 tình huống demo; chưa có bằng chứng khảo sát độc lập."""
    return [
        (
            UserPrefs(0.2, "Mới chơi (Newbie)", 1500000, True),
            ["Nanoflare 700 Play", "Power Control K520 Pro", "Nano Fusion Speed 722"],
        ),
        (
            UserPrefs(0.3, "Mới chơi (Newbie)", 800000, False),
            ["Power Control K520 Pro", "V200 Xanh", "TC88B"],
        ),
        (
            UserPrefs(0.7, "Mới chơi (Newbie)", 1600000, False),
            ["Astrox 77 Play", "V88 Cam", "TC88B"],
        ),
        (
            UserPrefs(0.1, "Phong trào (Intermediate)", 4000000, True),
            ["Windstorm 72", "Nanoflare 700 Play", "Brave Sword 12"],
        ),
        (
            UserPrefs(0.5, "Phong trào (Intermediate)", 3500000, False),
            ["Brave Sword 12", "Tectonic 7", "DriveX 9X"],
        ),
        (
            UserPrefs(0.5, "Phong trào (Intermediate)", 4500000, False),
            ["Arcsaber 11 Pro", "Halbertec 8000", "DriveX 9X"],
        ),
        (
            UserPrefs(0.8, "Phong trào (Intermediate)", 4200000, False),
            ["Thruster Ryuga II", "JPX Limited Edition", "Astrox 77 Play"],
        ),
        (
            UserPrefs(0.9, "Nâng cao / Bán chuyên (Advanced)", 5000000, False),
            ["Astrox 100ZZ", "Axforce 100", "Axforce 90 Max"],
        ),
        (
            UserPrefs(0.85, "Nâng cao / Bán chuyên (Advanced)", 4500000, False),
            ["Astrox 88D Pro", "Fortius 11 Quick", "Thruster Ryuga II"],
        ),
        (
            UserPrefs(0.6, "Nâng cao / Bán chuyên (Advanced)", 4500000, False),
            ["Arcsaber 11 Pro", "Halbertec 9000", "Astrox 88S Pro"],
        ),
        (
            UserPrefs(0.2, "Nâng cao / Bán chuyên (Advanced)", 4500000, False),
            ["Bladex 900 Moon", "Nanoflare 800 Pro", "AuraSpeed 90K II"],
        ),
        (
            UserPrefs(0.4, "Phong trào (Intermediate)", 1200000, True),
            ["Power Control K520 Pro", "Stroke 316", "TC88B"],
        ),
        (
            UserPrefs(0.75, "Nâng cao / Bán chuyên (Advanced)", 4200000, False),
            ["Duora Z-Strike", "Astrox 88D Pro", "JPX Limited Edition"],
        ),
        (
            UserPrefs(0.35, "Phong trào (Intermediate)", 3800000, False),
            ["Halbertec 8000", "Brave Sword 12", "Tectonic 7"],
        ),
        (
            UserPrefs(0.95, "Nâng cao / Bán chuyên (Advanced)", 4800000, False),
            ["Axforce 100", "Astrox 100ZZ", "Fortius 11 Quick"],
        ),
    ]


def _is_hit(predicted_models, true_keywords):
    for pred in predicted_models:
        for kw in true_keywords:
            if kw.lower() in pred.lower():
                return 1
    return 0


def evaluate_models_hit_at_3(catalog: pd.DataFrame) -> pd.DataFrame:
    """So sánh 3 thuật toán: Weighted Similarity, KNN và Decision Tree bằng độ đo Hit@3."""
    survey = get_ground_truth_survey()
    features = ["weight_g", "balance_score", "stiffness_score"]

    scales = pd.Series({"weight_g": 20.0, "balance_score": 4.0, "stiffness_score": 4.0})

    hits = {
        "Weighted Similarity (Đề xuất)": 0,
        "K-Nearest Neighbors (KNN)": 0,
        "Decision Tree": 0,
    }

    for prefs, truth_list in survey:
        eligible = filter_candidates(catalog, prefs)
        if eligible.empty:
            continue
        knn = NearestNeighbors(n_neighbors=min(3, len(eligible)), metric="euclidean")
        knn.fit(eligible[features] / scales)
        dt = DecisionTreeClassifier(max_depth=5, random_state=42)
        dt.fit(eligible[features], eligible["model"])
        rec_cos = recommend(catalog, prefs, k=3)
        hits["Weighted Similarity (Đề xuất)"] += _is_hit(
            rec_cos["model"].tolist(), truth_list
        )

        t_vec = ideal_vector(prefs)
        x_query = pd.DataFrame(
            [[t_vec["weight_g"], t_vec["balance_score"], t_vec["stiffness_score"]]],
            columns=features,
        )
        _, indices = knn.kneighbors(x_query / scales)
        knn_models = eligible.iloc[indices[0]]["model"].tolist()
        hits["K-Nearest Neighbors (KNN)"] += _is_hit(knn_models, truth_list)

        probs = dt.predict_proba(x_query)[0]
        top3_idx = np.argsort(probs)[::-1][:3]
        dt_models = [dt.classes_[i] for i in top3_idx]
        hits["Decision Tree"] += _is_hit(dt_models, truth_list)

    n = len(survey)
    results = [
        {
            "Mô hình": k,
            "Số ca đoán trúng (Hit)": v,
            "Tổng mẫu khảo sát": n,
            "Hit@3 (%)": round(v / n * 100, 1),
        }
        for k, v in hits.items()
    ]
    return pd.DataFrame(results)


def run_ablation_study(catalog: pd.DataFrame) -> pd.DataFrame:
    """Ablation Study: Lần lượt loại bỏ từng thông số để đánh giá sự suy giảm của Hit@3."""
    survey = get_ground_truth_survey()
    configs = {
        "Đầy đủ 3 thông số (Chuẩn)": {
            "weight_g": 0.25,
            "balance_score": 0.45,
            "stiffness_score": 0.30,
        },
        "Bỏ Điểm cân bằng (w_balance = 0)": {
            "weight_g": 0.45,
            "balance_score": 0.0,
            "stiffness_score": 0.55,
        },
        "Bỏ Độ cứng đũa (w_stiffness = 0)": {
            "weight_g": 0.35,
            "balance_score": 0.65,
            "stiffness_score": 0.0,
        },
        "Bỏ Trọng lượng (w_weight = 0)": {
            "weight_g": 0.0,
            "balance_score": 0.60,
            "stiffness_score": 0.40,
        },
    }
    rows = []
    for name, w in configs.items():
        h = 0
        for prefs, truth_list in survey:
            rec = recommend(catalog, prefs, k=3, weights=w)
            h += _is_hit(rec["model"].tolist(), truth_list)
        rows.append(
            {"Cấu hình Ablation": name, "Hit@3 (%)": round(h / len(survey) * 100, 1)}
        )
    return pd.DataFrame(rows)
