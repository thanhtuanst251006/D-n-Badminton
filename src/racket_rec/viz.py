import pandas as pd
import plotly.graph_objects as go


def radar_chart(df_top: pd.DataFrame, ideal: dict) -> go.Figure:
    categories = ["Trọng lượng (Quy đổi)", "Độ nặng đầu (1-5)", "Độ cứng đũa (1-5)"]
    fig = go.Figure()

    ideal_w_norm = min(5.0, max(1.0, (ideal["weight_g"] - 70) / 5.0))
    fig.add_trace(
        go.Scatterpolar(
            r=[ideal_w_norm, ideal["balance_score"], ideal["stiffness_score"]],
            theta=categories,
            fill="toself",
            name="Thông số lý tưởng của bạn",
            line={"color": "gold", "dash": "dash", "width": 3},
        )
    )

    for _, row in df_top.head(3).iterrows():
        w_norm = min(5.0, max(1.0, (row["weight_g"] - 70) / 5.0))
        fig.add_trace(
            go.Scatterpolar(
                r=[w_norm, row["balance_score"], row["stiffness_score"]],
                theta=categories,
                fill="toself",
                name=f"{row['brand']} {row['model']}",
            )
        )

    fig.update_layout(
        polar={"radialaxis": {"visible": True, "range": [0, 5]}},
        showlegend=True,
        margin={"l": 30, "r": 30, "t": 30, "b": 30},
    )
    return fig
