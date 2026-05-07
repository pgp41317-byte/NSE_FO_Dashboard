import pandas as pd
import numpy as np


def option_chain_summary(df):
    if df.empty:
        return {
            "total_call_oi": 0,
            "total_put_oi": 0,
            "pcr": 0,
            "max_call_oi_strike": None,
            "max_put_oi_strike": None,
            "market_view": "Data Not Available"
        }

    total_call_oi = df["CE OI"].sum()
    total_put_oi = df["PE OI"].sum()

    pcr = total_put_oi / total_call_oi if total_call_oi != 0 else 0

    max_call_oi_strike = df.loc[df["CE OI"].idxmax(), "Strike"]
    max_put_oi_strike = df.loc[df["PE OI"].idxmax(), "Strike"]

    if pcr > 1.2:
        market_view = "Bullish / Put Writing Strong"
    elif pcr < 0.8:
        market_view = "Bearish / Call Writing Strong"
    else:
        market_view = "Neutral"

    return {
        "total_call_oi": int(total_call_oi),
        "total_put_oi": int(total_put_oi),
        "pcr": round(pcr, 2),
        "max_call_oi_strike": max_call_oi_strike,
        "max_put_oi_strike": max_put_oi_strike,
        "market_view": market_view
    }


def detect_option_activity(df):
    if df.empty:
        return pd.DataFrame()

    result = df.copy()

    result["Net OI Change"] = result["PE Change OI"] - result["CE Change OI"]

    conditions = [
        result["Net OI Change"] > 0,
        result["Net OI Change"] < 0
    ]

    choices = [
        "Put Writing / Bullish Bias",
        "Call Writing / Bearish Bias"
    ]

    result["Signal"] = np.select(conditions, choices, default="Neutral")

    result["Activity Score"] = (
        result["CE Change OI"].abs()
        + result["PE Change OI"].abs()
        + result["CE Volume"]
        + result["PE Volume"]
    )

    result = result.sort_values("Activity Score", ascending=False)

    return result[
        [
            "Strike",
            "CE OI",
            "CE Change OI",
            "CE Volume",
            "PE OI",
            "PE Change OI",
            "PE Volume",
            "Net OI Change",
            "Signal",
            "Activity Score",
        ]
    ].head(25)