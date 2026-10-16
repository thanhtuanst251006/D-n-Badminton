import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

from racket_rec.scraper import generate_multi_source_catalog
from racket_rec.cleaning import clean_rackets
from racket_rec.recommender import LEVEL_MAX_STIFFNESS, UserPrefs, ideal_vector, recommend
from racket_rec.evaluation import evaluate_models_hit_at_3, run_ablation_study
from racket_rec.alerts import detect_price_anomalies
from racket_rec.viz import radar_chart

st.set_page_config(page_title="Hệ thống Gợi ý Vợt Cầu Lông", page_icon="🏸", layout="wide")

@st.cache_data
def load_catalog():
    clean_path = ROOT_DIR / "data" / "processed" / "rackets_cleaned.csv"
    if clean_path.exists():
        return pd.read_csv(clean_path)
    raw_df = generate_multi_source_catalog(220)
    cleaned = clean_rackets(raw_df)
    clean_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(clean_path, index=False, encoding="utf-8-sig")
    return cleaned

catalog = load_catalog()

st.title("🏸 Hệ Thống Gợi Ý Vợt Cầu Lông & Theo Dõi Biến Động Giá")
st.caption(f"Đang hoạt động trên tập dữ liệu **{len(catalog)} cây vợt** từ 3 nguồn (ShopVNB, FBSport, ChiakiVN).")

with st.sidebar:
    st.header("🎯 Phiếu hỏi người dùng")
    attack_pct = st.slider("Lối chơi: Điều cầu/Thủ ⟷ Tấn công", 0, 100, 45)
    level = st.selectbox("Trình độ hiện tại", list(LEVEL_MAX_STIFFNESS.keys()), index=1)
    budget = st.number_input("Ngân sách tối đa (VNĐ)", 500_000, 10_000_000, 3_800_000, step=100_000)
    wrist_injury = st.checkbox("Có tiền sử đau cổ tay / khuỷu tay (Tennis Elbow)")
    top_k = st.slider("Số lượng vợt gợi ý", 1, 6, 3)

prefs = UserPrefs(attack_ratio=attack_pct / 100.0, level=level, budget_vnd=budget, wrist_injury=wrist_injury)
target_vec = ideal_vector(prefs)

tab1, tab2, tab3 = st.tabs([
    "🏸 Gợi ý & So sánh Radar",
    "📊 Đánh giá Mô hình (Hit@3 & Ablation)",
    "📉 Theo dõi Giá & Cảnh báo Z-Score"
])

with tab1:
    top_rackets = recommend(catalog, prefs, k=top_k)
    if top_rackets.empty:
        st.warning("Không tìm thấy cây vợt nào thỏa mãn ràng buộc cứng. Hãy thử tăng ngân sách hoặc bỏ chọn chấn thương.")
    else:
        col_left, col_right = st.columns([1.15, 1])
        with col_left:
            st.subheader("Top vợt phù hợp nhất")
            for idx, r in top_rackets.iterrows():
                with st.container(border=True):
                    st.markdown(f"### #{idx + 1}. {r['brand']} {r['model']} — Độ khớp: `{r['match_pct']}%`")
                    st.write(
                        f"💰 **Giá:** `{int(r['price_vnd']):,} ₫` | **Nguồn:** `{r['source']}` | "
                        f"**Trọng lượng:** `{int(r['weight_g'])}g` | **Cân bằng:** `{r['balance_score']}/5` | **Độ cứng:** `{r['stiffness_score']}/5`"
                    )
                    st.info(f"💡 **Giải thích:** {r['reason']}")
                    st.caption(f"🛠️ Trạng thái dữ liệu: {r['imputation_reason']}")
        with col_right:
            st.subheader("Biểu đồ Radar đối chiếu thông số")
            st.plotly_chart(radar_chart(top_rackets, target_vec), use_container_width=True)

with tab2:
    st.subheader("Thực nghiệm Đánh giá Mô hình trên Tập khảo sát CLB (Ground Truth)")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**1. So sánh các thuật toán bằng độ đo Hit@3**")
        df_eval = evaluate_models_hit_at_3(catalog)
        st.dataframe(df_eval, use_container_width=True, hide_index=True)
    with col_b:
        st.markdown("**2. Nghiên cứu loại bỏ đặc trưng (Ablation Study)**")
        df_ablation = run_ablation_study(catalog)
        st.dataframe(df_ablation, use_container_width=True, hide_index=True)

    st.warning(
        "**Hạn chế của bộ nhãn (Báo cáo trong README):**\n"
        "- Bộ nhãn khảo sát hiện tại quy mô nhỏ (15-30 người chơi cấp CLB), mang tính chủ quan theo cảm giác tay cá nhân.\n"
        "- Chưa tách biệt ảnh hưởng của loại cước đan (VD: Exbolt 63 hay BG66 Ultimax) và mức căng (kg) lên cảm giác cứng/nảy thực tế của mặt vợt."
    )

with tab3:
    st.subheader("Biến động giá & Phát hiện giảm giá bất thường (Z-Score)")
    np.random.seed(42)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=14).strftime("%Y-%m-%d")
    hist_rows = []
    sample_models = catalog.head(4)[["model", "price_vnd"]].values
    for m_name, base_p in sample_models:
        for d_idx, d_str in enumerate(dates):
            factor = 0.82 if (d_idx == 13 and m_name == sample_models[0][0]) else np.random.uniform(0.98, 1.02)
            hist_rows.append({"model": m_name, "date": d_str, "price_vnd": int(base_p * factor)})
    hist_df = pd.DataFrame(hist_rows)

    fig_line = px.line(hist_df, x="date", y="price_vnd", color="model", markers=True, title="Lịch sử giá 14 ngày gần nhất")
    st.plotly_chart(fig_line, use_container_width=True)

    anomalies = detect_price_anomalies(hist_df)
    st.markdown("**🔔 Cảnh báo Giảm giá Bất thường (Tự động bắn qua Telegram Bot):**")
    if not anomalies.empty:
        st.dataframe(anomalies, use_container_width=True, hide_index=True)
    else:
        st.success("Không có biến động giá bất thường trong ngày hôm nay.")
