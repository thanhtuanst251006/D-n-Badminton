from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app/streamlit_app.py"


def demo_app():
    at = AppTest.from_file(str(APP), default_timeout=30)
    at.session_state["data_mode"] = "Demo thuật toán"
    return at.run()


def test_app_filters_and_empty_results():
    at = demo_app()
    assert not at.exception
    assert at.metric[0].value == "220"
    at.multiselect(key="brands").set_value(["Yonex"]).run()
    at.text_input(key="search").set_value("Astrox").run()
    at.session_state["view"] = "Danh mục vợt"
    at.run()
    assert not at.exception
    results = at.dataframe[0].value
    assert not results.empty
    assert results["brand"].eq("Yonex").all()
    assert results["model"].str.contains("Astrox").all()
    assert results["price_vnd"].le(3_800_000).all()
    at.number_input(key="budget").set_value(0).run()
    assert not at.exception
    assert at.metric[1].value == "0"
    assert len(at.warning) == 1


def test_app_all_views_and_price_selection():
    at = demo_app()
    for view in ["Danh mục vợt", "Đánh giá mô hình", "Theo dõi giá"]:
        at.session_state["view"] = view
        at.run()
        assert not at.exception
    assert len(at.dataframe) == 1
    at.multiselect(key="price_models").set_value([]).run()
    assert not at.exception
    assert any("Chọn ít nhất" in item.value for item in at.info)
    at.multiselect(key="brands").set_value(["Kumpoo"]).run()
    assert not at.exception
    assert at.multiselect(key="price_models").value == []
    assert pd.notna(at.metric[1].value)


def test_real_catalog_filters_links_and_zero_budget():
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not at.exception
    assert at.selectbox(key="data_mode").value == "Giá thật từ shop"
    assert int(at.metric[0].value) > 220
    assert at.metric[1].value == "3"
    at.multiselect(key="real_shops").set_value(["HVShop"]).run()
    at.multiselect(key="real_brands").set_value(["Victor"]).run()
    assert not at.exception
    rows = at.dataframe[0].value
    assert not rows.empty
    assert rows["source"].eq("HVShop").all()
    assert rows["brand"].eq("Victor").all()
    assert rows["product_url"].str.startswith("https://hvshop.vn/").all()
    at.toggle(key="real_contact").set_value(False).run()
    at.number_input(key="real_budget").set_value(0).run()
    assert not at.exception
    assert at.metric[2].value == "0"
    assert at.warning


def test_real_recommendations_provenance_and_mode_switch():
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    at.session_state["real_view"] = "Gợi ý có thông số"
    at.run()
    assert not at.exception
    assert len(at.get("link_button")) == 3
    at.session_state["real_view"] = "Nguồn dữ liệu"
    at.run()
    assert not at.exception
    assert len(at.dataframe[0].value) == 3
    at.selectbox(key="data_mode").select("Demo thuật toán").run()
    assert not at.exception
    assert at.metric[0].value == "220"
