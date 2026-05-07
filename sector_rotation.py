import pandas as pd
import plotly.express as px


SECTOR_MAP = {
    "RELIANCE": "Energy",
    "ONGC": "Energy",
    "COALINDIA": "Energy",
    "ADANIGREEN": "Energy",
    "ADANIPOWER": "Energy",

    "TCS": "IT",
    "INFY": "IT",
    "WIPRO": "IT",
    "TECHM": "IT",
    "HCLTECH": "IT",

    "HDFCBANK": "Banking",
    "ICICIBANK": "Banking",
    "SBIN": "Banking",
    "KOTAKBANK": "Banking",
    "AXISBANK": "Banking",
    "INDUSINDBK": "Banking",

    "LT": "Capital Goods",
    "SIEMENS": "Capital Goods",
    "ABB": "Capital Goods",

    "ITC": "FMCG",
    "HINDUNILVR": "FMCG",
    "NESTLEIND": "FMCG",
    "BRITANNIA": "FMCG",

    "MARUTI": "Auto",
    "TATAMOTORS": "Auto",
    "EICHERMOT": "Auto",
    "HEROMOTOCO": "Auto",

    "SUNPHARMA": "Pharma",
    "DRREDDY": "Pharma",
    "CIPLA": "Pharma",
    "DIVISLAB": "Pharma",

    "ULTRACEMCO": "Cement",
    "AMBUJACEM": "Cement",
    "GRASIM": "Cement",

    "ADANIENT": "Infrastructure",
    "ADANIPORTS": "Infrastructure",
    "DLF": "Real Estate",
    "LODHA": "Real Estate",

    "BAJFINANCE": "Financial Services",
    "BAJAJFINSV": "Financial Services",

    "BHARTIARTL": "Telecom",

    "JSWSTEEL": "Metals",
    "VEDL": "Metals",

    "TITAN": "Consumer Discretionary",
    "ASIANPAINT": "Consumer Discretionary",
    "PIDILITIND": "Consumer Discretionary",
    "HAVELLS": "Consumer Discretionary",

    "INDIGO": "Aviation",
}


def add_sector_column(scanner_df):
    if scanner_df.empty:
        return scanner_df

    df = scanner_df.copy()
    df["Sector"] = df["Symbol"].map(SECTOR_MAP).fillna("Others")
    return df


def sector_summary(scanner_df):
    if scanner_df.empty:
        return pd.DataFrame()

    df = add_sector_column(scanner_df)

    summary = df.groupby("Sector").agg(
        Stocks=("Symbol", "count"),
        Avg_Day_Change=("Day Change %", "mean"),
        Avg_5m_Change=("5m Change %", "mean"),
        Avg_Volume_Ratio=("Volume Ratio", "mean"),
        Avg_Strength=("Strength", "mean"),
        Buying_Count=("Signal", lambda x: x.astype(str).str.contains("Buying|Positive", case=False).sum()),
        Selling_Count=("Signal", lambda x: x.astype(str).str.contains("Selling|Negative", case=False).sum()),
    ).reset_index()

    summary["Net_Buying_Pressure"] = summary["Buying_Count"] - summary["Selling_Count"]

    summary = summary.sort_values("Avg_Strength", ascending=False)

    return summary.round(2)


def sector_bar_chart(summary_df):
    if summary_df.empty:
        return None

    fig = px.bar(
        summary_df,
        x="Sector",
        y="Avg_Day_Change",
        color="Net_Buying_Pressure",
        hover_data=[
            "Stocks",
            "Avg_5m_Change",
            "Avg_Volume_Ratio",
            "Avg_Strength",
            "Buying_Count",
            "Selling_Count"
        ],
        title="Sector Rotation — Average Day Change & Buying Pressure"
    )

    fig.update_layout(
        height=550,
        xaxis_title="Sector",
        yaxis_title="Average Day Change %",
    )

    return fig


def sector_strength_chart(summary_df):
    if summary_df.empty:
        return None

    fig = px.bar(
        summary_df.sort_values("Avg_Strength", ascending=False),
        x="Sector",
        y="Avg_Strength",
        color="Avg_Day_Change",
        hover_data=[
            "Stocks",
            "Avg_Volume_Ratio",
            "Net_Buying_Pressure"
        ],
        title="Sector Strength Ranking"
    )

    fig.update_layout(
        height=550,
        xaxis_title="Sector",
        yaxis_title="Average Strength Score",
    )

    return fig


def sector_leaders_laggards(scanner_df):
    if scanner_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    df = add_sector_column(scanner_df)

    leaders = df.sort_values(["Day Change %", "Strength"], ascending=False).head(20)
    laggards = df.sort_values(["Day Change %", "Strength"], ascending=[True, False]).head(20)

    return leaders, laggards