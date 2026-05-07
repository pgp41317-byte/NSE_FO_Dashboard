import pandas as pd
import plotly.express as px


def classify_futures_proxy(row):
    price_change = row.get("Day Change %", 0)
    volume_ratio = row.get("Volume Ratio", 0)

    if price_change > 1 and volume_ratio > 1.5:
        return "Long Buildup Proxy"

    elif price_change < -1 and volume_ratio > 1.5:
        return "Short Buildup Proxy"

    elif price_change > 1 and volume_ratio < 1:
        return "Short Covering Proxy"

    elif price_change < -1 and volume_ratio < 1:
        return "Long Unwinding Proxy"

    elif volume_ratio > 2:
        return "High Futures-Like Activity"

    else:
        return "Neutral"


def futures_strength(row):
    price_change = abs(row.get("Day Change %", 0))
    volume_ratio = row.get("Volume Ratio", 0)

    score = 0
    score += min(price_change * 20, 50)
    score += min(volume_ratio * 25, 50)

    return round(min(score, 100), 1)


def create_futures_buildup_table(scanner_df):
    if scanner_df.empty:
        return pd.DataFrame()

    df = scanner_df.copy()

    df["Futures Signal"] = df.apply(classify_futures_proxy, axis=1)
    df["Futures Strength"] = df.apply(futures_strength, axis=1)

    df = df.sort_values("Futures Strength", ascending=False)

    return df[
        [
            "Symbol",
            "Price",
            "Day Change %",
            "5m Change %",
            "Volume Ratio",
            "Signal",
            "Futures Signal",
            "Futures Strength",
            "Time"
        ]
    ]


def futures_signal_summary(futures_df):
    if futures_df.empty:
        return pd.DataFrame()

    summary = futures_df.groupby("Futures Signal").agg(
        Count=("Symbol", "count"),
        Avg_Day_Change=("Day Change %", "mean"),
        Avg_Volume_Ratio=("Volume Ratio", "mean"),
        Avg_Strength=("Futures Strength", "mean")
    ).reset_index()

    return summary.round(2).sort_values("Avg_Strength", ascending=False)


def futures_buildup_chart(futures_df):
    if futures_df.empty:
        return None

    filtered = futures_df[futures_df["Futures Signal"] != "Neutral"].copy()

    if filtered.empty:
        filtered = futures_df.head(20)

    fig = px.scatter(
        filtered,
        x="Day Change %",
        y="Volume Ratio",
        size="Futures Strength",
        color="Futures Signal",
        hover_data=["Symbol", "Price", "5m Change %", "Signal"],
        title="Futures Buildup Proxy Scanner — Price vs Volume Pressure"
    )

    fig.update_layout(
        height=650,
        xaxis_title="Day Change %",
        yaxis_title="Volume Ratio"
    )

    return fig


def top_long_short_tables(futures_df):
    if futures_df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    long_buildup = futures_df[futures_df["Futures Signal"] == "Long Buildup Proxy"].head(20)
    short_buildup = futures_df[futures_df["Futures Signal"] == "Short Buildup Proxy"].head(20)
    short_covering = futures_df[futures_df["Futures Signal"] == "Short Covering Proxy"].head(20)
    long_unwinding = futures_df[futures_df["Futures Signal"] == "Long Unwinding Proxy"].head(20)

    return long_buildup, short_buildup, short_covering, long_unwinding