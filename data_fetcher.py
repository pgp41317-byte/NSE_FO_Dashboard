import requests
import pandas as pd
import yfinance as yf
from config import NSE_BASE_URL
def get_yf_live_price(ticker, fallback_price=None):
    try:
        fi = yf.Ticker(ticker).fast_info

        price = (
            fi.get("last_price")
            or fi.get("lastPrice")
            or fi.get("regular_market_price")
            or fi.get("regularMarketPrice")
        )

        if price is not None:
            return float(price)

    except Exception:
        pass

    return float(fallback_price) if fallback_price is not None else None

def get_yfinance_index_data(symbol_map):
    rows = []

    for name, ticker in symbol_map.items():
        try:
            data = yf.Ticker(ticker).history(period="5d", interval="5m")

            if data.empty or "Close" not in data.columns:
                rows.append({"Index": name, "Price": "NA", "Change %": "NA"})
                continue

            close = data["Close"].dropna()

            candle_latest = float(close.iloc[-1])
            previous = float(close.iloc[-2]) if len(close) > 1 else candle_latest

            latest = get_yf_live_price(ticker, candle_latest)

            change_pct = ((latest - previous) / previous) * 100 if previous else 0

            rows.append({
                "Index": name,
                "Price": round(latest, 2),
                "Change %": round(change_pct, 2)
            })

        except Exception as e:
            rows.append({
                "Index": name,
                "Price": "Error",
                "Change %": str(e)[:40]
            })

    return pd.DataFrame(rows)


def create_nse_session():
    session = requests.Session()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0 Safari/537.36",
        "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
        "Referer": "https://www.nseindia.com/option-chain",
        "Connection": "keep-alive",
    }

    session.headers.update(headers)

    try:
        session.get("https://www.nseindia.com", timeout=10)
        session.get("https://www.nseindia.com/option-chain", timeout=10)
    except Exception:
        pass

    return session


def get_option_chain(symbol="NIFTY"):
    session = create_nse_session()

    urls = [
        f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}",
        f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}",
    ]

    for url in urls:
        try:
            response = session.get(url, timeout=15)

            if response.status_code != 200:
                continue

            raw_data = response.json()
            records = raw_data.get("records", {}).get("data", [])

            rows = []

            for item in records:
                strike = item.get("strikePrice")

                ce = item.get("CE", {})
                pe = item.get("PE", {})

                rows.append({
                    "Strike": strike,

                    "CE OI": ce.get("openInterest", 0),
                    "CE Change OI": ce.get("changeinOpenInterest", 0),
                    "CE Volume": ce.get("totalTradedVolume", 0),
                    "CE LTP": ce.get("lastPrice", 0),

                    "PE OI": pe.get("openInterest", 0),
                    "PE Change OI": pe.get("changeinOpenInterest", 0),
                    "PE Volume": pe.get("totalTradedVolume", 0),
                    "PE LTP": pe.get("lastPrice", 0),
                })

            df = pd.DataFrame(rows)

            if not df.empty:
                return df.sort_values("Strike").reset_index(drop=True)

        except Exception as e:
            print("NSE fetch error:", e)

    return get_demo_option_chain(symbol)


def get_demo_option_chain(symbol="NIFTY"):
    if symbol == "BANKNIFTY":
        strikes = list(range(48000, 51000, 100))
    else:
        strikes = list(range(22000, 23500, 50))

    rows = []

    for strike in strikes:
        rows.append({
            "Strike": strike,
            "CE OI": abs(23500 - strike) * 20 + 10000,
            "CE Change OI": (strike % 7) * 1200 - 3000,
            "CE Volume": (strike % 9) * 1500 + 5000,
            "CE LTP": max(1, abs(23000 - strike) / 10),

            "PE OI": abs(strike - 22500) * 25 + 12000,
            "PE Change OI": (strike % 11) * 1000 - 2500,
            "PE Volume": (strike % 8) * 1700 + 4000,
            "PE LTP": max(1, abs(strike - 22500) / 10),
        })

    return pd.DataFrame(rows)