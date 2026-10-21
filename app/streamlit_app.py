import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

import pandas as pd
import plotly.express as px
import streamlit as st

from racket_rec.alerts import detect_price_anomalies, generate_demo_history
from racket_rec.cleaning import clean_rackets
from racket_rec.evaluation import evaluate_models_hit_at_3, run_ablation_study
from racket_rec.recommender import (
    LEVEL_MAX_STIFFNESS,
    UserPrefs,
    filter_candidates,
    ideal_vector,
    recommend,
)
from racket_rec.scraper import generate_multi_source_catalog
from racket_rec.shop_ui import show_shop_catalog
from racket_rec.viz import radar_chart

st.set_page_config(
    page_title="Racket Pro · Tìm vợt hợp bạn", page_icon="🏸", layout="wide"
)


@st.cache_data(ttl=3600, max_entries=2)
def load_catalog(modified_ns: int) -> pd.DataFrame:
    """Invalidate cache when the catalog changes; never write files on rerun."""
    path = ROOT_DIR / "data/processed/rackets_cleaned.csv"
    if path.exists():
        return pd.read_csv(path)
    return clean_rackets(generate_multi_source_catalog(220))


@st.cache_data(ttl=3600, max_entries=4)
def evaluate_catalog(catalog: pd.DataFrame):
    return evaluate_models_hit_at_3(catalog), run_ablation_study(catalog)


def money(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".") + " ₫"


st.title("🏸 Racket Pro")
st.caption("Tìm vợt hợp bạn, xem giá từ các shop.")
data_mode = st.sidebar.selectbox(
    "Dữ liệu", ["Giá thật từ shop", "Demo thuật toán"], key="data_mode"
)
if data_mode == "Giá thật từ shop":
    show_shop_catalog(ROOT_DIR)
    st.stop()

catalog_path = ROOT_DIR / "data/processed/rackets_cleaned.csv"
catalog = load_catalog(catalog_path.stat().st_mtime_ns if catalog_path.exists() else 0)
st.info(
    "Bản demo: danh mục và lịch sử giá là dữ liệu mô phỏng; tên nguồn chỉ là nhãn minh họa.",
    icon=":material/info:",
)

with st.sidebar:
    st.header("Hồ sơ của bạn", anchor=False)
    attack_pct = st.slider("Thiên về tấn công (%)", 0, 100, 45, key="attack")
    st.caption("0%: điều cầu / phòng thủ · 100%: chuyên công")
    level = st.selectbox("Trình độ", list(LEVEL_MAX_STIFFNESS), index=1, key="level")
    budget = st.number_input(
        "Ngân sách tối đa (VNĐ)", 0, 10_000_000, 3_800_000, step=100_000, key="budget"
    )
    wrist_injury = st.toggle("Ưu tiên vợt nhẹ, đũa mềm", key="wrist")
    st.caption("Bật để giới hạn trọng lượng ≤ 84g và độ cứng ≤ 3,2/5.")
    top_k = st.slider("Số vợt gợi ý", 1, 6, 3, key="top_k")
    st.subheader("Thu hẹp lựa chọn", anchor=False)
    brands = st.multiselect(
        "Thương hiệu", sorted(catalog["brand"].unique()), key="brands"
    )
    sources = st.multiselect(
        "Nguồn minh họa", sorted(catalog["source"].unique()), key="sources"
    )
    query = st.text_input(
        "Tìm tên vợt", placeholder="Ví dụ: Astrox, Brave Sword…", key="search"
    )
    st.caption("Racket Pro · Portfolio demo")

prefs = UserPrefs(attack_pct / 100, level, budget, wrist_injury)
filtered = catalog
if brands:
    filtered = filtered[filtered["brand"].isin(brands)]
if sources:
    filtered = filtered[filtered["source"].isin(sources)]
if query.strip():
    filtered = filtered[
        filtered["model"].str.contains(query.strip(), case=False, regex=False, na=False)
    ]
candidates = filter_candidates(filtered, prefs)
top_rackets = recommend(filtered, prefs, k=top_k)
metrics = st.columns(3)
metrics[0].metric("Vợt trong danh mục", len(catalog), border=True)
metrics[1].metric("Đáp ứng lựa chọn", len(candidates), border=True)
metrics[2].metric("Ngân sách của bạn", money(budget), border=True)
view = st.segmented_control(
    "Khám phá",
    ["Gợi ý cho bạn", "Danh mục vợt", "Theo dõi giá", "Đánh giá mô hình"],
    default="Gợi ý cho bạn",
    key="view",
)

if view == "Gợi ý cho bạn":
    if top_rackets.empty:
        st.warning(
            "Chưa có vợt phù hợp. Thử tăng ngân sách, đổi từ khóa hoặc xóa bộ lọc thương hiệu / nguồn."
        )
    else:
        left, right = st.columns([1.1, 1])
        with left:
            st.subheader("Lựa chọn dành cho bạn", anchor=False)
            for idx, row in top_rackets.iterrows():
                with st.container(border=True):
                    st.caption(f"LỰA CHỌN {idx + 1} · {row['brand']} · {row['source']}")
                    st.subheader(row["model"], anchor=False)
                    st.markdown(
                        f"**{money(row['price_vnd'])}** · :green[Độ khớp {row['match_pct']}%]"
                    )
                    st.progress(float(row["match_pct"]) / 100)
                    st.caption(
                        f"{row['weight_g']:g} g · Cân bằng {row['balance_score']:g}/5 · Độ cứng {row['stiffness_score']:g}/5"
                    )
                    with st.expander("Vì sao vợt này phù hợp?"):
                        st.write(row["reason"])
                        st.caption(f"Chất lượng dữ liệu: {row['imputation_reason']}")
        with right:
            st.subheader("So sánh với mục tiêu", anchor=False)
            st.plotly_chart(
                radar_chart(top_rackets, ideal_vector(prefs)),
                width="stretch",
                alt="So sánh thông số tối đa 3 vợt với mục tiêu.",
            )
            st.caption(
                "Radar hiển thị tối đa 3 vợt đầu tiên; trọng lượng được quy đổi sang thang 1–5."
            )
            st.caption(
                "Độ khớp là điểm tương đồng thông số, không phải xác suất hài lòng khi sử dụng."
            )
        st.download_button(
            "Tải danh sách gợi ý",
            top_rackets.to_csv(index=False).encode("utf-8-sig"),
            "racket-pro-goi-y.csv",
            "text/csv",
            icon=":material/download:",
        )

elif view == "Danh mục vợt":
    st.subheader("Danh mục đáp ứng hồ sơ", anchor=False)
    st.caption(
        "Áp dụng toàn bộ bộ lọc, ngân sách và giới hạn thông số trong hồ sơ của bạn."
    )
    if candidates.empty:
        st.warning("Không có kết quả với bộ lọc hiện tại.")
    else:
        sort = st.selectbox(
            "Sắp xếp", ["Giá tăng dần", "Giá giảm dần", "Tên vợt"], key="sort"
        )
        ordered = candidates.sort_values(
            "model" if sort == "Tên vợt" else "price_vnd",
            ascending=sort != "Giá giảm dần",
        )
        display = ordered[
            [
                "brand",
                "model",
                "price_vnd",
                "weight_g",
                "balance_score",
                "stiffness_score",
                "source",
            ]
        ]
        st.dataframe(
            display,
            hide_index=True,
            width="stretch",
            alt="Danh mục vợt đáp ứng bộ lọc.",
            column_config={
                "brand": "Hãng",
                "model": "Tên vợt",
                "price_vnd": st.column_config.NumberColumn(
                    "Giá demo (VNĐ)", format="localized"
                ),
                "weight_g": "Trọng lượng (g)",
                "balance_score": "Cân bằng /5",
                "stiffness_score": "Độ cứng /5",
                "source": "Nguồn minh họa",
            },
        )
        st.download_button(
            "Tải danh mục đã lọc",
            display.to_csv(index=False).encode("utf-8-sig"),
            "racket-pro-danh-muc.csv",
            "text/csv",
            icon=":material/download:",
        )

elif view == "Theo dõi giá":
    st.subheader("Lịch sử giá mô phỏng", anchor=False)
    st.caption(
        "Dữ liệu demo 14 ngày có cài sẵn một mức giảm để minh họa. Ứng dụng chưa theo dõi giá trực tuyến hoặc tự gửi Telegram."
    )
    if candidates.empty:
        st.warning("Không có vợt đáp ứng bộ lọc để xem lịch sử giá.")
    else:
        models = st.multiselect(
            "Chọn tối đa 4 vợt",
            candidates["model"].unique().tolist(),
            default=candidates["model"].head(4).tolist(),
            max_selections=4,
            key="price_models",
        )
        if models:
            selected = candidates[candidates["model"].isin(models)]
            today = pd.Timestamp.now(tz="Asia/Ho_Chi_Minh").date()
            history = generate_demo_history(selected, end_date=str(today))
            fig = px.line(
                history,
                x="date",
                y="price_vnd",
                color="model",
                markers=True,
                labels={"date": "Ngày", "price_vnd": "Giá demo (VNĐ)", "model": "Vợt"},
            )
            st.plotly_chart(
                fig,
                width="stretch",
                alt="Lịch sử giá mô phỏng trong 14 ngày của các vợt đã chọn.",
            )
            anomalies = detect_price_anomalies(history)
            if anomalies.empty:
                st.success("Không phát hiện mức giảm vượt ngưỡng trong dữ liệu demo.")
            else:
                st.markdown("**Mức giảm bất thường trong dữ liệu demo**")
                st.dataframe(
                    anomalies,
                    hide_index=True,
                    width="stretch",
                    alt="Các mức giảm giá bất thường trong dữ liệu demo.",
                )
        else:
            st.info("Chọn ít nhất một vợt để xem biểu đồ.")

elif view == "Đánh giá mô hình":
    st.subheader("Thử nghiệm trên 15 tình huống mẫu", anchor=False)
    st.caption(
        "Các tình huống và nhãn được khai báo trong mã nguồn, chưa có bằng chứng khảo sát độc lập. Kết quả phục vụ minh họa, không đại diện hiệu quả thực tế."
    )
    st.caption(
        "Đánh giá dùng toàn bộ danh mục; cả ba mô hình áp dụng cùng ràng buộc ngân sách và thông số. KNN chuẩn hóa theo miền đặc trưng; Decision Tree học ánh xạ thông số → tên vợt trong danh mục."
    )
    evaluation, ablation = evaluate_catalog(catalog)
    st.dataframe(
        evaluation,
        hide_index=True,
        width="stretch",
        alt="Hit@3 của ba mô hình trên 15 tình huống mẫu.",
    )
    st.subheader("Ảnh hưởng của từng thông số", anchor=False)
    st.dataframe(
        ablation,
        hide_index=True,
        width="stretch",
        alt="Kết quả đánh giá khi lần lượt loại bỏ từng đặc trưng.",
    )
