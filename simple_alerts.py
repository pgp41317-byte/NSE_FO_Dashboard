import pandas as pd
import yfinance as yf
from datetime import datetime
from nifty500 import NIFTY500


def scan_simple_market(limit=100):
    tickers = NIFTY500[:limit]

    data = yf.download(
        tickers=tickers,
        period="7d",
        interval="5m",
        group_by="ticker",
        auto_adjust=False,
        progress=False,
        threads=True
    )

    rows = []

    for ticker in tickers:
        try:
            df = data[ticker].dropna()

            if df.empty or len(df) < 30:
                continue

            latest = df.iloc[-1]
            previous = df.iloc[-2]

            price = float(latest["Close"])
            prev_price = float(previous["Close"])

            day_df = df[df.index.date == df.index[-1].date()]

            day_high = float(day_df["High"].max())
            day_low = float(day_df["Low"].min())

            week_high = float(df["High"].max())
            week_low = float(df["Low"].min())

            prev_day_close = float(df[df.index.date < df.index[-1].date()]["Close"].iloc[-1])

            day_change = ((price - prev_day_close) / prev_day_close) * 100 if prev_day_close else 0
            five_min_change = ((price - prev_price) / prev_price) * 100

            latest_volume = float(latest["Volume"])
            avg_volume = float(df["Volume"].tail(30).mean())
            volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 0

            alerts = []

            if day_change >= 1.5 and volume_ratio >= 1.2:
                alerts.append("Huge Buying")

            if day_change <= -1.5 and volume_ratio >= 1.2:
                alerts.append("Huge Selling")

            if price >= day_high * 0.999:
                alerts.append("Day High Breakout")

            if price <= day_low * 1.001:
                alerts.append("Day Low Breakdown")

            if price >= week_high * 0.999:
                alerts.append("Week High Breakout")

            if price <= week_low * 1.001:
                alerts.append("Week Low Breakdown")

            if five_min_change >= 0.5 and volume_ratio >= 1.2:
                alerts.append("Sudden 5m Buying")

            if five_min_change <= -0.5 and volume_ratio >= 1.2:
                alerts.append("Sudden 5m Selling")

            alert_text = ", ".join(alerts) if alerts else "No Alert"

            strength = min(
                abs(day_change) * 20 + abs(five_min_change) * 25 + volume_ratio * 20,
                100
            )

            rows.append({
                "Symbol": ticker.replace(".NS", ""),
                "Price": round(price, 2),
                "Day Change %": round(day_change, 2),
                "5m Change %": round(five_min_change, 2),
                "Volume Ratio": round(volume_ratio, 2),
                "Day High": round(day_high, 2),
                "Day Low": round(day_low, 2),
                "Week High": round(week_high, 2),
                "Week Low": round(week_low, 2),
                "Alert": alert_text,
                "Strength": round(strength, 1),
                "Time": datetime.now().strftime("%H:%M:%S")
            })

        except Exception:
            continue

    result = pd.DataFrame(rows)

    if result.empty:
        return result

    return result.sort_values("Strength", ascending=False)


def only_active_alerts(df):
    if df.empty:
        return df

    return df[df["Alert"] != "No Alert"].sort_values("Strength", ascending=False)