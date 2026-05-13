import pandas as pd
import yfinance as yf
from datetime import datetime
from nifty500 import NIFTY500


def fetch_batch_data(tickers):
    try:
        data = yf.download(
            tickers=tickers,
            period="2d",
            interval="5m",
            group_by="ticker",
            auto_adjust=False,
            progress=False,
            threads=True
        )

        return data

    except Exception:
        return pd.DataFrame()


def calculate_signal(day_change, candle_change, volume_ratio):

    if day_change > 2 and volume_ratio > 1.5:
        return "Aggressive Buying"

    elif day_change < -2 and volume_ratio > 1.5:
        return "Aggressive Selling"

    elif candle_change > 0.5 and volume_ratio > 1.2:
        return "Momentum Buying"

    elif candle_change < -0.5 and volume_ratio > 1.2:
        return "Momentum Selling"

    elif volume_ratio > 2:
        return "Volume Explosion"

    elif abs(day_change) > 3:
        return "Large Directional Move"

    else:
        return "Normal"


def strength_score(day_change, candle_change, volume_ratio):

    score = 0

    score += min(abs(day_change) * 12, 40)
    score += min(abs(candle_change) * 18, 25)
    score += min(volume_ratio * 20, 35)

    return round(min(score, 100), 1)


def scan_cash_market():

    batch_data = fetch_batch_data(NIFTY500)

    rows = []

    for ticker in NIFTY500:

        try:
            stock = batch_data[ticker]

            stock = stock.dropna()

            if len(stock) < 10:
                continue

            latest = stock.iloc[-1]
            previous = stock.iloc[-2]

            latest_price = latest["Close"]
            prev_price = previous["Close"]

            candle_change = (
                (latest_price - prev_price) / prev_price
            ) * 100

            prev_day_close = stock[stock.index.date < stock.index[-1].date()]["Close"].iloc[-1]

            day_change = ((latest_price - prev_day_close) / prev_day_close) * 100 if prev_day_close else 0  

            latest_volume = latest["Volume"]

            avg_volume = stock["Volume"].tail(20).mean()

            volume_ratio = (
                latest_volume / avg_volume
                if avg_volume > 0 else 0
            )

            signal = calculate_signal(
                day_change,
                candle_change,
                volume_ratio
            )

            strength = strength_score(
                day_change,
                candle_change,
                volume_ratio
            )

            rows.append({
                "Symbol": ticker.replace(".NS", ""),
                "Price": round(latest_price, 2),
                "Day Change %": round(day_change, 2),
                "5m Change %": round(candle_change, 2),
                "Volume Ratio": round(volume_ratio, 2),
                "Latest Volume": int(latest_volume),
                "Signal": signal,
                "Strength": strength,
                "Time": datetime.now().strftime("%H:%M:%S")
            })

        except Exception:
            continue

    result = pd.DataFrame(rows)

    if result.empty:
        return result

    return result.sort_values(
        "Strength",
        ascending=False
    )


def get_live_alerts(scanner_df):

    if scanner_df.empty:
        return pd.DataFrame()

    alerts = scanner_df[
        scanner_df["Strength"] >= 40
    ]

    alerts = alerts[
        alerts["Signal"] != "Normal"
    ]

    return alerts.sort_values(
        "Strength",
        ascending=False
    )