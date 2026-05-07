import plotly.express as px
import pandas as pd


def create_market_heatmap(scanner_df):
    if scanner_df.empty:
        return None

    df = scanner_df.copy()

    df["Color Value"] = df["Day Change %"]
    df["Size Value"] = df["Strength"]

    fig = px.treemap(
        df,
        path=["Signal", "Symbol"],
        values="Size Value",
        color="Color Value",
        hover_data=[
            "Price",
            "Day Change %",
            "5m Change %",
            "Volume Ratio",
            "Strength",
            "Time"
        ],
        color_continuous_scale="RdYlGn",
        title="Market Heatmap — Buying/Selling Pressure"
    )

    fig.update_layout(
        height=750,
        margin=dict(t=50, l=10, r=10, b=10)
    )

    return fig


def create_top_movers_table(scanner_df):
    if scanner_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    gainers = scanner_df.sort_values("Day Change %", ascending=False).head(15)
    losers = scanner_df.sort_values("Day Change %", ascending=True).head(15)

    return gainers, losers


def create_volume_spike_table(scanner_df):
    if scanner_df.empty:
        return pd.DataFrame()

    return scanner_df.sort_values("Volume Ratio", ascending=False).head(20)