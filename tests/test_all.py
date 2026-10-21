import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from racket_rec.cleaning import clean_price, clean_rackets, clean_weight
from racket_rec.recommender import UserPrefs, recommend


def test_clean_price_concatenated():
    assert clean_price("499.000 ₫") == 499000
    assert clean_price("499000499000638000") == 499000


def test_clean_weight():
    assert clean_weight("4U (80-84g)") == 83.0
    assert clean_weight("3U") == 88.0


def test_wrist_injury_constraint():
    raw = pd.DataFrame(
        [
            {
                "title": "Vợt Nặng",
                "brand": "Yonex",
                "model": "100ZZ",
                "price_raw": "4.200.000",
                "weight_raw": "3U",
                "balance_raw": "Siêu nặng",
                "stiffness_raw": "Siêu cứng",
                "source": "VNB",
            },
            {
                "title": "Vợt Nhẹ",
                "brand": "Kumpoo",
                "model": "K520",
                "price_raw": "650.000",
                "weight_raw": "4U",
                "balance_raw": "Cân bằng",
                "stiffness_raw": "Dẻo",
                "source": "VNB",
            },
        ]
    )
    catalog = clean_rackets(raw)
    prefs = UserPrefs(
        attack_ratio=0.5,
        level="Phong trào (Intermediate)",
        budget_vnd=5000000,
        wrist_injury=True,
    )
    res = recommend(catalog, prefs, k=5)
    assert len(res) == 1
    assert res.iloc[0]["model"] == "K520"


def test_zero_budget_is_a_hard_constraint():
    from racket_rec.recommender import filter_candidates

    catalog = pd.DataFrame(
        [{"price_vnd": 500000, "weight_g": 83, "stiffness_score": 2.5}]
    )
    prefs = UserPrefs(0.5, "Mới chơi (Newbie)", 0)
    assert filter_candidates(catalog, prefs).empty
    assert recommend(catalog, prefs).empty


def test_balance_all_round_label():
    from racket_rec.cleaning import clean_balance

    assert clean_balance("Công thủ toàn diện") == 3.0
    assert clean_balance("Nặng đầu, thiên công") == 4.3


def test_evaluation_small_empty_and_unaffordable_catalogs():
    from racket_rec.evaluation import evaluate_models_hit_at_3

    catalog = pd.DataFrame(
        [
            {
                "model": "Astrox 100ZZ",
                "price_vnd": 20_000_000,
                "weight_g": 83,
                "balance_score": 4.8,
                "stiffness_score": 5.0,
            }
        ]
    )
    result = evaluate_models_hit_at_3(catalog)
    assert result["Hit@3 (%)"].eq(0).all()
    assert evaluate_models_hit_at_3(catalog.iloc[:0])["Hit@3 (%)"].eq(0).all()
    catalog["price_vnd"] = 500000
    result = evaluate_models_hit_at_3(catalog)
    assert len(result) == 3
    assert result["Hit@3 (%)"].between(0, 100).all()


def test_demo_price_drop_and_stable_history():
    from racket_rec.alerts import detect_price_anomalies, generate_demo_history

    catalog = pd.DataFrame(
        [
            {"model": "Demo A", "price_vnd": 1000000},
            {"model": "Demo B", "price_vnd": 2000000},
        ]
    )
    first = generate_demo_history(catalog, "2026-10-21")
    pd.testing.assert_frame_equal(first, generate_demo_history(catalog, "2026-10-21"))
    assert len(first) == 28
    assert first["date"].max() == "2026-10-21"
    alerts = detect_price_anomalies(first.sample(frac=1, random_state=7))
    assert alerts["model"].tolist() == ["Demo A"]
    assert alerts.iloc[0]["drop_pct"] >= 8
    first["price_vnd"] = 1000000
    assert detect_price_anomalies(first).empty
