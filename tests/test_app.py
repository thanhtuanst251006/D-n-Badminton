from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app/streamlit_app.py"


def test_app_filters_and_empty_results():
    at = AppTest.from_file(str(APP), default_timeout=30).run()
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
    at = AppTest.from_file(str(APP), default_timeout=30).run()
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
