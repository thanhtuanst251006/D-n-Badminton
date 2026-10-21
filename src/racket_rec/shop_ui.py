"""Streamlit views for real offers, separate from synthetic demonstrations."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from racket_rec.live_catalog import load_snapshot
from racket_rec.recommender import (
    LEVEL_MAX_STIFFNESS,
    UserPrefs,
    filter_candidates,
    ideal_vector,
    recommend,
)
from racket_rec.viz import radar_chart


@st.cache_data(ttl=300, max_entries=4)
def read_offers(directory: str, modified_ns: int) -> pd.DataFrame:
    return load_snapshot(Path(directory))


def show_offer_table(offers: pd.DataFrame) -> None:
    columns = [
        "brand",
        "model",
        "source",
        "price_vnd",
        "price_max_vnd",
        "price_text",
        "weight_raw",
        "balance_raw",
        "stiffness_raw",
        "availability",
        "collected_at",
        "product_url",
    ]
    st.dataframe(
        offers[columns],
        hide_index=True,
        width="stretch",
        alt="Các chào bán từ shop, gồm giá công bố, thông số nguyên bản, thời điểm ghi nhận và liên kết sản phẩm.",
        column_config={
            "brand": "Thương hiệu",
            "model": "Dòng vợt / phiên bản",
            "source": "Shop",
            "price_vnd": st.column_config.NumberColumn(
                "Giá từ (VNĐ)", format="localized"
            ),
            "price_max_vnd": st.column_config.NumberColumn(
                "Đến (VNĐ)", format="localized"
            ),
            "price_text": "Giá shop công bố",
            "weight_raw": "Trọng lượng shop ghi",
            "balance_raw": "Cân bằng shop ghi",
            "stiffness_raw": "Độ cứng shop ghi",
            "availability": "Tình trạng",
            "collected_at": "Ghi nhận lúc (UTC)",
            "product_url": st.column_config.LinkColumn(
                "Sản phẩm", display_text="Xem tại shop"
            ),
        },
    )
    st.download_button(
        "Tải danh mục giá thật",
        offers[columns].to_csv(index=False).encode("utf-8-sig"),
        "racket-pro-gia-shop.csv",
        "text/csv",
        icon=":material/download:",
        key="real_download",
    )


def show_shop_catalog(root: Path) -> None:
    directory = root / "data/processed"
    path = directory / "shop_offers.csv"
    if not path.exists():
        st.warning(
            "Chưa có bản ghi giá thật. Chạy lệnh cập nhật danh mục từ thư mục dự án:"
        )
        st.code(
            '$env:PYTHONPATH="src"; python -m racket_rec.live_catalog --pages 10 --details 30',
            language="powershell",
        )
        return
    catalog = read_offers(str(directory), path.stat().st_mtime_ns)
    if catalog.empty:
        st.warning("Danh mục giá thật đang trống.")
        return
    latest = (
        pd.to_datetime(catalog["collected_at"], utc=True)
        .max()
        .tz_convert("Asia/Ho_Chi_Minh")
    )
    st.caption(
        f"Giá công bố trên trang shop · Ghi nhận gần nhất: {latest:%d/%m/%Y %H:%M} (giờ Việt Nam). Mỗi dòng là một chào bán; cùng mẫu có thể xuất hiện ở nhiều shop."
    )
    st.info(
        "Giá là bản ghi tại thời điểm thu thập, có thể thay đổi theo phiên bản và khuyến mãi. Mở link shop để kiểm tra giá cuối cùng, tồn kho, cước và phí vận chuyển.",
        icon=":material/storefront:",
    )
    with st.sidebar:
        st.header("Tìm vợt tại các shop", anchor=False)
        query = st.text_input(
            "Tên vợt / dòng vợt",
            placeholder="Astrox, Nanoflare, Axforce…",
            key="real_query",
        )
        shops = st.multiselect(
            "Shop", sorted(catalog["source"].unique()), key="real_shops"
        )
        brands = st.multiselect(
            "Thương hiệu", sorted(catalog["brand"].unique()), key="real_brands"
        )
        budget = st.number_input(
            "Ngân sách tối đa (VNĐ)",
            0,
            20_000_000,
            5_000_000,
            step=100_000,
            key="real_budget",
        )
        contact = st.toggle("Hiện cả giá liên hệ", value=True, key="real_contact")
        st.caption(
            "Danh mục giá không lọc theo độ cứng, để bạn vẫn xem được vợt chưa đủ thông số."
        )
    filtered = catalog.copy()
    if query.strip():
        filtered = filtered[
            filtered["title"].str.contains(
                query.strip(), case=False, regex=False, na=False
            )
        ]
    if shops:
        filtered = filtered[filtered["source"].isin(shops)]
    if brands:
        filtered = filtered[filtered["brand"].isin(brands)]
    over_budget = filtered[filtered["price_vnd"].gt(budget)]
    within_budget = filtered["price_vnd"].le(budget)
    if contact:
        within_budget |= filtered["price_vnd"].isna()
    filtered = filtered[within_budget]
    cols = st.columns(4)
    cols[0].metric("Chào bán thật", len(catalog), border=True)
    cols[1].metric("Shop có dữ liệu", catalog["source"].nunique(), border=True)
    cols[2].metric("Đáp ứng bộ lọc", len(filtered), border=True)
    cols[3].metric(
        "Đủ thông số để gợi ý", int(filtered["specs_complete"].sum()), border=True
    )
    view = st.segmented_control(
        "Khám phá giá thật",
        ["Danh mục các shop", "Gợi ý có thông số", "Nguồn dữ liệu"],
        default="Danh mục các shop",
        key="real_view",
    )
    if view == "Danh mục các shop":
        st.subheader("Nhiều dòng vợt, nhiều nơi bán", anchor=False)
        st.caption(
            "Lọc theo giá thấp nhất shop niêm yết; khoảng giá giữ nguyên. Ô thông số trống nghĩa là chưa ghi nhận được từ shop. Các dòng có tên gần giống chưa chắc cùng phiên bản."
        )
        if query.strip() and not over_budget.empty:
            lowest = f"{over_budget['price_vnd'].min():,.0f}".replace(",", ".")
            limit = f"{budget:,.0f}".replace(",", ".")
            st.info(
                f"Có {len(over_budget)} chào bán khớp từ khóa đang bị ẩn vì vượt ngân sách {limit} ₫. "
                f"Giá ghi nhận thấp nhất trong nhóm này là {lowest} ₫. "
                "Tăng ngân sách ở thanh bên để xem các kết quả đó.",
                icon=":material/filter_alt:",
            )
        if filtered.empty:
            st.warning("Không có kết quả. Thử đổi từ khóa, shop hoặc ngân sách.")
            return
        sort = st.selectbox(
            "Sắp xếp",
            ["Giá tăng dần", "Giá giảm dần", "Thương hiệu / tên vợt", "Shop"],
            key="real_sort",
        )
        fields = (
            ["brand", "model"]
            if sort == "Thương hiệu / tên vợt"
            else ["source", "model"]
            if sort == "Shop"
            else ["price_vnd", "model"]
        )
        ordered = filtered.sort_values(
            fields, ascending=sort != "Giá giảm dần", na_position="last"
        )
        show_offer_table(ordered)
    elif view == "Gợi ý có thông số":
        st.subheader("Chỉ chấm điểm vợt có thông số từ shop", anchor=False)
        st.caption(
            "Không tự điền trọng lượng, độ cứng, cân bằng hay giá. Với khoảng giá, toàn bộ khoảng phải nằm trong ngân sách. Điểm 1–5 và trọng lượng theo nhóm U là quy đổi gần đúng; xem thông số gốc tại shop trước khi chọn."
        )
        attack = st.slider("Thiên về tấn công (%)", 0, 100, 45, key="real_attack")
        level = st.selectbox(
            "Trình độ", list(LEVEL_MAX_STIFFNESS), index=1, key="real_level"
        )
        light = st.toggle("Ưu tiên vợt nhẹ, đũa mềm", key="real_light")
        prefs = UserPrefs(attack / 100, level, budget, light)
        eligible = filter_candidates(filtered, prefs)
        top = recommend(eligible, prefs, k=3)
        if top.empty:
            st.warning(
                "Chưa có vợt đủ thông số đáp ứng hồ sơ. Bạn vẫn có thể tra cứu giá và link trong danh mục các shop."
            )
            return
        for i, row in top.iterrows():
            with st.container(border=True):
                st.subheader(f"{i + 1}. {row['model']}", anchor=False)
                st.markdown(
                    f"**{row['source']} · {row['price_text']}** · Độ khớp {row['match_pct']}%"
                )
                st.caption(
                    f"Shop công bố: {row['weight_raw']} · {row['balance_raw']} · {row['stiffness_raw']}"
                )
                st.write(row["reason"])
                st.link_button(
                    "Xem giá và sản phẩm tại shop",
                    row["product_url"],
                    icon=":material/open_in_new:",
                )
        st.plotly_chart(
            radar_chart(top, ideal_vector(prefs)),
            width="stretch",
            alt="Thông số quy đổi của ba chào bán phù hợp nhất so với mục tiêu.",
        )
    elif view == "Nguồn dữ liệu":
        st.subheader("Phạm vi và thời điểm ghi nhận", anchor=False)
        status_path = directory / "shop_status.json"
        if status_path.exists():
            status = json.loads(status_path.read_text(encoding="utf-8"))
            for entry in status:
                if entry.get("errors"):
                    st.warning(
                        f"{entry['shop']}: lần cập nhật gần nhất có lỗi; có thể đang giữ một phần dữ liệu cũ. Xem thời điểm ghi nhận theo từng chào bán."
                    )
        summary = (
            catalog.groupby("source")
            .agg(
                chao_ban=("product_url", "nunique"),
                thuong_hieu=("brand", "nunique"),
                du_thong_so=("specs_complete", "sum"),
                ghi_nhan_som_nhat=("collected_at", "min"),
                ghi_nhan_moi_nhat=("collected_at", "max"),
            )
            .reset_index()
        )
        st.dataframe(
            summary,
            hide_index=True,
            width="stretch",
            alt="Số lượng chào bán, thương hiệu, thông số và thời điểm thu thập theo shop.",
        )
        st.caption(
            "Mới thu thập một phần danh mục mỗi shop, không bảo đảm bao phủ toàn bộ thị trường. Giá liên hệ không được tự thay bằng giá ước tính. Chưa có lịch sử giá thật theo ngày; phần lịch sử mô phỏng nằm riêng trong Demo thuật toán."
        )
        st.markdown(
            "Nguồn: [ShopVNB](https://shopvnb.com/vot-cau-long.html) · [FBShop](https://fbshop.vn/vot-cau-long/) · [HVShop](https://hvshop.vn/vot-cau-long/)"
        )
