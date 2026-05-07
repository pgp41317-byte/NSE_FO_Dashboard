import pandas as pd
import plotly.express as px


def classify_delivery_proxy(row):
    day_change = row.get("Day Change %", 0)
    volume_ratio = row.get("Volume Ratio", 0)

    if volume_ratio >= 2 and day_change > 1:
        return "Strong Accumulation Proxy"

    elif volume_ratio >= 2 and day_change < -1:
        return "Strong Distribution Proxy"

    elif volume_ratio >= 1.5 and day_change > 0:
        return "Accumulation Bias"

    elif volume_ratio >= 1.5 and day_change < 0:
        return "Distribution Bias"

    elif volume_ratio >= 2:
        return "Unusual Delivery-Like Volume"

    else:
        return "Normal"


def delivery_strength(row):
    day_change = abs(row.get("Day Change %", 0))
    volume_ratio = row.get("Volume Ratio", 0)

    score = 0
    score += min(volume_ratio * 30, 60)
    score += min(day_change * 15, 40)

    return round(min(score, 100), 1)


def create_delivery_table(scanner_df):
    if scanner_df.empty:
        return pd.DataFrame()

    df = scanner_df.copy()

    df["Delivery Signal"] = df.apply(classify_delivery_proxy, axis=1)
    df["Delivery Strength"] = df.apply(delivery_strength, axis=1)

    df = df.sort_values("Delivery Strength", ascending=False)

    return df[
        [
            "Symbol",
            "Price",
            "Day Change %",
            "5m Change %",
            "Volume Ratio",
            "Latest Volume",
            "Signal",
            "Delivery Signal",
            "Delivery Strength",
            "Time"
        ]
    ]


def delivery_summary(delivery_df):
    if delivery_df.empty:
        return pd.DataFrame()

    summary = delivery_df.groupby("Delivery Signal").agg(
        Count=("Symbol", "count"),
        Avg_Day_Change=("Day Change %", "mean"),
        Avg_Volume_Ratio=("Volume Ratio", "mean"),
        Avg_Delivery_Strength=("Delivery Strength", "mean")
    ).reset_index()

    return summary.round(2).sort_values("Avg_Delivery_Strength", ascending=False)


def delivery_chart(delivery_df):
    if delivery_df.empty:
        return None

    filtered = delivery_df[delivery_df["Delivery Signal"] != "Normal"]

    if filtered.empty:
        filtered = delivery_df.head(25)

    fig = px.scatter(
        filtered,
        x="Day Change %",
        y="Volume Ratio",
        size="Delivery Strength",
        color="Delivery Signal",
        hover_data=["Symbol", "Price", "5m Change %", "Latest Volume"],
        title="Delivery Spike Proxy — Volume Accumulation / Distribution"
    )

    fig.update_layout(
        height=650,
        xaxis_title="Day Change %",
        yaxis_title="Volume Ratio"
    )

    return fig


def top_accumulation_distribution(delivery_df):
    if delivery_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    accumulation = delivery_df[
        delivery_df["Delivery Signal"].astype(str).str.contains("Accumulation", case=False)
    ].head(25)

    distribution = delivery_df[
        delivery_df["Delivery Signal"].astype(str).str.contains("Distribution", case=False)
    ].head(25)

    return accumulation, distribution