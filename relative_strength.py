import pandas as pd
import plotly.express as px


def create_relative_strength_table(scanner_df, nifty_change=0):
    if scanner_df.empty:
        return pd.DataFrame()

    df = scanner_df.copy()

    df["Benchmark Change %"] = nifty_change
    df["Relative Strength %"] = df["Day Change %"] - nifty_change

    df["RS Signal"] = df["Relative Strength %"].apply(classify_rs_signal)

    df["RS Score"] = (
        abs(df["Relative Strength %"]) * 25
        + df["Volume Ratio"] * 15
        + df["Strength"] * 0.4
    )

    df["RS Score"] = df["RS Score"].clip(upper=100).round(1)

    return df.sort_values("RS Score", ascending=False)


def classify_rs_signal(rs):
    if rs >= 2:
        return "Strong Outperformer"
    elif rs >= 1:
        return "Outperformer"
    elif rs <= -2:
        return "Strong Underperformer"
    elif rs <= -1:
        return "Underperformer"
    else:
        return "Market Performer"


def rs_summary(rs_df):
    if rs_df.empty:
        return pd.DataFrame()

    return (
        rs_df.groupby("RS Signal")
        .agg(
            Count=("Symbol", "count"),
            Avg_RS=("Relative Strength %", "mean"),
            Avg_Day_Change=("Day Change %", "mean"),
            Avg_Volume_Ratio=("Volume Ratio", "mean"),
            Avg_RS_Score=("RS Score", "mean"),
        )
        .reset_index()
        .round(2)
        .sort_values("Avg_RS_Score", ascending=False)
    )


def rs_scatter_chart(rs_df):
    if rs_df.empty:
        return None

    fig = px.scatter(
        rs_df,
        x="Relative Strength %",
        y="Volume Ratio",
        size="RS Score",
        color="RS Signal",
        hover_data=[
            "Symbol",
            "Price",
            "Day Change %",
            "Benchmark Change %",
            "5m Change %",
            "Strength",
        ],
        title="Relative Strength Scanner — Stock vs NIFTY"
    )

    fig.update_layout(
        height=650,
        xaxis_title="Relative Strength vs NIFTY %",
        yaxis_title="Volume Ratio"
    )

    return fig


def top_outperformers_underperformers(rs_df):
    if rs_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    outperformers = rs_df.sort_values("Relative Strength %", ascending=False).head(25)
    underperformers = rs_df.sort_values("Relative Strength %", ascending=True).head(25)

    return outperformers, underperformers