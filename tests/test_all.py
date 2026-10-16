import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
from racket_rec.cleaning import clean_price, clean_weight, clean_rackets
from racket_rec.recommender import UserPrefs, recommend

def test_clean_price_concatenated():
    assert clean_price("499.000 ₫") == 499000
    assert clean_price("499000499000638000") == 499000

def test_clean_weight():
    assert clean_weight("4U (80-84g)") == 83.0
    assert clean_weight("3U") == 88.0

def test_wrist_injury_constraint():
    raw = pd.DataFrame([
        {"title": "Vợt Nặng", "brand": "Yonex", "model": "100ZZ", "price_raw": "4.200.000", "weight_raw": "3U", "balance_raw": "Siêu nặng", "stiffness_raw": "Siêu cứng", "source": "VNB"},
        {"title": "Vợt Nhẹ", "brand": "Kumpoo", "model": "K520", "price_raw": "650.000", "weight_raw": "4U", "balance_raw": "Cân bằng", "stiffness_raw": "Dẻo", "source": "VNB"},
    ])
    catalog = clean_rackets(raw)
    prefs = UserPrefs(attack_ratio=0.5, level="Phong trào (Intermediate)", budget_vnd=5000000, wrist_injury=True)
    res = recommend(catalog, prefs, k=5)
    assert len(res) == 1
    assert res.iloc[0]["model"] == "K520"
