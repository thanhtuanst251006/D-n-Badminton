import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from racket_rec.cleaning import clean_stiffness
from racket_rec.live_catalog import (
    SHOPS,
    load_snapshot,
    normalize_specs,
    parse_detail_specs,
    parse_listing,
    parse_price,
    save_snapshot,
)
from racket_rec.recommender import UserPrefs, filter_candidates

STAMP = "2026-10-21T06:00:00+00:00"


def test_current_price_range_and_contact():
    assert parse_price("499.000 - 638.000 ₫") == (499000, 638000, "range")
    assert parse_price("239.000đ") == (239000, 239000, "exact")
    assert parse_price("Liên hệ") == (None, None, "contact")
    assert parse_price("Từ 2.000.000đ") == (2000000, 2000000, "from")
    html = """<div class="product type-product"><h3 class="product-title"><a href="/vot-cau-long-vicleo-turbo-7/">Vợt cầu lông Vicleo Turbo 7</a></h3>
    <span class="price"><del>450.000 ₫</del><ins>340.000 ₫<span class="screen-reader-text">Giá hiện tại là 340000</span></ins></span>
    <div class="attr-item">Hơi dẻo</div><div class="attr-item">Hơi nặng đầu</div><div class="attr-item">4U</div></div>"""
    row = parse_listing(html, SHOPS["HVShop"], STAMP)[0]
    assert row["price_vnd"] == row["price_max_vnd"] == 340000
    assert row["specs_complete"]
    assert row["brand"] == "VicLeo"


def test_listing_no_imputation_duplicate_links_and_external_domains():
    html = """<div class="prd-card"><a class="prd-card-link" href="/p/vot-cau-long-yonex/">Vợt Cầu Lông Yonex Arcsaber 11</a><span class="price-current">Liên hệ</span></div>"""
    external = html.replace("/p/vot-cau-long-yonex/", "https://example.com/product")
    rows = parse_listing(html + html + external, SHOPS["FBShop"], STAMP)
    assert len(rows) == 1
    row = rows[0]
    assert row["source"] == "FBShop"
    assert row["collected_at"] == STAMP
    assert row["product_url"] == "https://fbshop.vn/p/vot-cau-long-yonex/"
    assert row["price_vnd"] is None
    assert row["weight_g"] is None
    assert not row["specs_complete"]


def test_vnb_range_and_exclude_bundles():
    html = """<div class="item_product_main"><span class="product-name"><a href="vot-v88.html">Vợt cầu lông VNB V88 xanh</a></span><div class="price-box"><span class="price">499.000 - 638.000 ₫</span></div></div>"""
    rows = parse_listing(
        html + html.replace("Vợt cầu lông VNB", "Combo vợt cầu lông VNB"),
        SHOPS["ShopVNB"],
        STAMP,
    )
    assert len(rows) == 1
    assert rows[0]["price_vnd"] == 499000
    assert rows[0]["price_max_vnd"] == 638000
    assert rows[0]["product_url"] == "https://shopvnb.com/vot-v88.html"


def test_explicit_specs_and_ambiguous_weights():
    html = """<table><tr><td>Trọng Lượng:</td><td>4U: 80 - 84g</td></tr><tr><td>Điểm Cân Bằng:</td><td>Nặng Đầu</td></tr><tr><td>Độ Cứng Đũa:</td><td>Trung Bình</td></tr></table>
    <div class="mona-content"><p>– Độ cứng thân vợt: Cứng trung bình</p></div>"""
    row = normalize_specs(parse_detail_specs(html))
    assert row["specs_complete"]
    assert row["stiffness_score"] == 3.0
    assert clean_stiffness("Cứng Trung Bình") == 3.0
    row["weight_raw"] = "3U / 4U"
    assert not normalize_specs(row)["specs_complete"]


def test_real_recommendation_requires_specs_and_affordable_range():
    base = {
        "price_vnd": 500000,
        "price_max_vnd": 800000,
        "weight_g": 83,
        "balance_score": 3,
        "stiffness_score": 3,
        "specs_complete": True,
        "availability": "Cần kiểm tra tại shop",
    }
    catalog = pd.DataFrame(
        [
            base,
            {**base, "specs_complete": False},
            {**base, "availability": "Shop ghi hết hàng"},
        ]
    )
    prefs = UserPrefs(0.5, "Mới chơi (Newbie)", 600000)
    assert filter_candidates(catalog, prefs).empty
    prefs.budget_vnd = 1000000
    assert len(filter_candidates(catalog, prefs)) == 1


def test_snapshot_preserves_failed_shop_and_old_file_on_empty(tmp_path):
    first = pd.DataFrame(
        [
            {
                "source": "ShopVNB",
                "price_vnd": 500000,
                "price_max_vnd": 500000,
                "weight_g": None,
                "balance_score": None,
                "stiffness_score": None,
            },
            {
                "source": "HVShop",
                "price_vnd": 600000,
                "price_max_vnd": 600000,
                "weight_g": 83,
                "balance_score": 3,
                "stiffness_score": 3,
            },
        ]
    )
    save_snapshot(first, [], tmp_path)
    save_snapshot(
        first.iloc[:1],
        [{"shop": "HVShop", "offers": 0, "errors": ["HTTP 403"]}],
        tmp_path,
    )
    loaded = load_snapshot(tmp_path)
    assert set(loaded["source"]) == {"ShopVNB", "HVShop"}
    assert loaded.loc[loaded["source"].eq("HVShop"), "specs_complete"].all()
    save_snapshot(pd.DataFrame(), [], tmp_path)
    assert len(load_snapshot(tmp_path)) == 2
