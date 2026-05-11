"""
╔══════════════════════════════════════════════════════════════╗
║         NIFTY 50 LIVE DASHBOARD  ──  Auto-refresh 60s       ║
╠══════════════════════════════════════════════════════════════╣
║  WHAT IT FETCHES EVERY 60 SECONDS:                          ║
║  • NIFTY 50 price, open, high, low, volume, prev close      ║
║  • India VIX (fear gauge) + intraday VIX chart              ║
║  • NIFTY BANK index price + change                          ║
║  • USD/INR exchange rate                                    ║
║  • 52-week high & low, P/E ratio, Market cap                ║
║  • 1-year realised volatility                               ║
║  • 30-day OHLCV candlestick chart                           ║
║  • Top 10 NIFTY stocks (price, %, volume, 52W, P/E, Mcap)  ║
║  • Monte Carlo simulation (10,000 paths, 30 days)           ║
║  • Full percentile table P1→P99                             ║
║  • Options pricing: Call + Put (MC + Black-Scholes)         ║
║  • All Greeks: Delta, Gamma, Theta, Vega                    ║
║  • 10-scenario probability grid with animated bars          ║
║  • Trading recommendation (BUY CALL / PUT / SPREAD etc.)    ║
║                                                             ║
║  SETUP (run once in VS Code terminal):                      ║
║    pip install yfinance numpy scipy pandas                  ║
║                                                             ║
║  RUN:                                                       ║
║    python nifty_live_dashboard.py                           ║
║                                                             ║
║  The script:                                                ║
║   1. Fetches all live data via yfinance                     ║
║   2. Runs Monte Carlo simulation                            ║
║   3. Writes  nifty_dashboard_live.html                      ║
║   4. Opens your browser automatically                       ║
║   5. Repeats every 60 seconds                               ║
║   6. The HTML page itself also auto-refreshes in browser    ║
╚══════════════════════════════════════════════════════════════╝
"""

import yfinance as yf
import numpy as np
import math
import json
import time
import os
import threading
import webbrowser
from scipy.stats import norm
from datetime import datetime

# ─────────────────────────────────────────────────────────────
#  SETTINGS
# ─────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "nifty_dashboard_live.html")
REFRESH_SECONDS  = 60           # how often to fetch + rebuild (seconds)
HIST_VOL_ANN     = 0.2014       # 18-year NIFTY historical vol
ANNUAL_DRIFT     = 0.0895       # 18-year historical drift
RISK_FREE        = 0.065        # India 10Y bond yield (annual)
N_PATHS          = 10000        # Monte Carlo paths (30-day sim)
HORIZON          = 30           # simulation days
OPT_PATHS        = 100000       # option pricing paths (higher = more accurate)
STRIKE           = 24500        # option strike price
T_DAYS           = 21           # days to option expiry

# Top NIFTY 50 stocks to track individually
TOP_STOCKS = {
    "RELIANCE.NS":   "Reliance",
    "TCS.NS":        "TCS",
    "HDFCBANK.NS":   "HDFC Bank",
    "INFY.NS":       "Infosys",
    "ICICIBANK.NS":  "ICICI Bank",
    "HINDUNILVR.NS": "HUL",
    "ITC.NS":        "ITC",
    "KOTAKBANK.NS":  "Kotak Bank",
    "LT.NS":         "L&T",
    "AXISBANK.NS":   "Axis Bank",
}

# ─────────────────────────────────────────────────────────────
#  STEP 1 — FETCH ALL LIVE MARKET DATA
# ─────────────────────────────────────────────────────────────
def fetch_all():
    data = {}

    # ── NIFTY 50 index ─────────────────────────────────────
    print("  [1/4] Fetching NIFTY 50...")
    try:
        nsei     = yf.Ticker("^NSEI")
        info     = nsei.info
        hist_1d  = nsei.history(period="1d",  interval="1m")
        hist_30d = nsei.history(period="1mo", interval="1d")
        hist_1y  = nsei.history(period="1y",  interval="1d")

        price      = float(hist_1d["Close"].iloc[-1])   if not hist_1d.empty  else 24000.0
        open_p     = float(hist_1d["Open"].iloc[0])     if not hist_1d.empty  else price
        high_d     = float(hist_1d["High"].max())       if not hist_1d.empty  else price
        low_d      = float(hist_1d["Low"].min())        if not hist_1d.empty  else price
        volume     = int(hist_1d["Volume"].sum())        if not hist_1d.empty  else 0
        prev_close = float(info.get("previousClose", price))
        wk52_high  = float(info.get("fiftyTwoWeekHigh", price * 1.1))
        wk52_low   = float(info.get("fiftyTwoWeekLow",  price * 0.9))
        pe_ratio   = info.get("trailingPE",  None)
        mkt_cap    = info.get("marketCap",   None)

        # 30-day OHLCV for candlestick chart
        candles = []
        if not hist_30d.empty:
            for idx, row in hist_30d.iterrows():
                candles.append({
                    "date":   str(idx)[:10],
                    "open":   round(float(row["Open"]),  2),
                    "high":   round(float(row["High"]),  2),
                    "low":    round(float(row["Low"]),   2),
                    "close":  round(float(row["Close"]), 2),
                    "volume": int(row["Volume"]),
                })

        # 1-year realised volatility
        if not hist_1y.empty and len(hist_1y) > 20:
            log_rets     = np.log(hist_1y["Close"] / hist_1y["Close"].shift(1)).dropna()
            realised_vol = float(log_rets.std() * math.sqrt(252) * 100)
        else:
            realised_vol = HIST_VOL_ANN * 100

        data["nifty"] = {
            "price":        round(price, 2),
            "open":         round(open_p, 2),
            "high":         round(high_d, 2),
            "low":          round(low_d, 2),
            "volume":       volume,
            "prev_close":   round(prev_close, 2),
            "day_change":   round(price - prev_close, 2),
            "day_pct":      round((price / prev_close - 1) * 100, 2) if prev_close else 0.0,
            "wk52_high":    round(wk52_high, 2),
            "wk52_low":     round(wk52_low, 2),
            "pe_ratio":     round(pe_ratio, 2) if pe_ratio else "N/A",
            "mkt_cap":      mkt_cap,
            "realised_vol": round(realised_vol, 2),
            "candles":      candles,
        }
        print(f"    ✓ NIFTY 50: ₹{price:,.2f}  ({data['nifty']['day_pct']:+.2f}%)")
    except Exception as e:
        print(f"    ✗ NIFTY error: {e}")
        data["nifty"] = {
            "price": 24000.0, "open": 24000.0, "high": 24100.0, "low": 23900.0,
            "volume": 0, "prev_close": 23950.0, "day_change": 50.0, "day_pct": 0.21,
            "wk52_high": 26373.0, "wk52_low": 22182.0, "pe_ratio": "N/A",
            "mkt_cap": None, "realised_vol": 20.14, "candles": [],
        }

    # ── INDIA VIX ──────────────────────────────────────────
    print("  [2/4] Fetching India VIX...")
    try:
        vix_t      = yf.Ticker("^INDIAVIX")
        vix_hist   = vix_t.history(period="1d", interval="1m")
        vix        = float(vix_hist["Close"].iloc[-1]) if not vix_hist.empty else 18.0
        vix_series = [round(float(v), 2) for v in vix_hist["Close"].tolist()] if not vix_hist.empty else []
        print(f"    ✓ India VIX: {vix:.2f}%")
    except Exception as e:
        print(f"    ✗ VIX error: {e}")
        vix = 18.0
        vix_series = []

    data["vix"]        = round(vix, 2)
    data["vix_series"] = vix_series

    # ── NIFTY BANK + USD/INR ───────────────────────────────
    print("  [3/4] Fetching NIFTY Bank + USD/INR...")
    try:
        nb_t    = yf.Ticker("^NSEBANK")
        nb_hist = nb_t.history(period="1d", interval="1m")
        nb_info = nb_t.info
        nb_p    = float(nb_hist["Close"].iloc[-1]) if not nb_hist.empty else 51000.0
        nb_prev = float(nb_info.get("previousClose", nb_p))
        nb_pct  = round((nb_p / nb_prev - 1) * 100, 2) if nb_prev else 0.0
        print(f"    ✓ NIFTY Bank: ₹{nb_p:,.2f}  ({nb_pct:+.2f}%)")
    except Exception as e:
        print(f"    ✗ NIFTY Bank error: {e}")
        nb_p, nb_pct = 51000.0, 0.0

    try:
        fx_t    = yf.Ticker("USDINR=X")
        fx_hist = fx_t.history(period="1d", interval="1m")
        usdinr  = float(fx_hist["Close"].iloc[-1]) if not fx_hist.empty else 84.5
        print(f"    ✓ USD/INR: ₹{usdinr:.2f}")
    except Exception as e:
        print(f"    ✗ USD/INR error: {e}")
        usdinr = 84.5

    data["niftybank"] = {"price": round(nb_p, 2), "day_pct": nb_pct}
    data["usdinr"]    = round(usdinr, 2)

    # ── TOP 10 STOCKS ──────────────────────────────────────
    print("  [4/4] Fetching top 10 NIFTY stocks...")
    stocks = []
    for ticker, name in TOP_STOCKS.items():
        try:
            t    = yf.Ticker(ticker)
            inf  = t.info
            h5m  = t.history(period="1d", interval="5m")
            sp   = float(h5m["Close"].iloc[-1])  if not h5m.empty else float(inf.get("regularMarketPrice", 0))
            svol = int(h5m["Volume"].sum())       if not h5m.empty else 0
            sprev= float(inf.get("previousClose", sp))
            spct = round((sp / sprev - 1) * 100, 2) if sprev else 0.0
            stocks.append({
                "ticker":  ticker.replace(".NS", ""),
                "name":    name,
                "price":   round(sp, 2),
                "change":  round(sp - sprev, 2),
                "pct":     spct,
                "volume":  svol,
                "high52":  round(float(inf.get("fiftyTwoWeekHigh", sp * 1.1)), 2),
                "low52":   round(float(inf.get("fiftyTwoWeekLow",  sp * 0.9)), 2),
                "mcap":    inf.get("marketCap", None),
                "pe":      round(float(inf.get("trailingPE", 0)), 2) if inf.get("trailingPE") else None,
            })
            print(f"    ✓ {name}: ₹{sp:,.2f}  ({spct:+.2f}%)")
            time.sleep(0.25)   # polite rate-limit pause
        except Exception as e:
            print(f"    ✗ {name}: {e}")
            stocks.append({
                "ticker": ticker.replace(".NS",""), "name": name,
                "price": 0.0, "change": 0.0, "pct": 0.0, "volume": 0,
                "high52": 0.0, "low52": 0.0, "mcap": None, "pe": None,
            })

    data["stocks"] = stocks
    return data


# ─────────────────────────────────────────────────────────────
#  STEP 2 — MONTE CARLO + OPTIONS SIMULATION
# ─────────────────────────────────────────────────────────────
def run_simulation(price, vix):
    print("  Running Monte Carlo (10,000 paths × 30 days)...")
    np.random.seed(int(time.time()) % 99999)

    blend_vol   = 0.70 * (vix / 100.0) + 0.30 * HIST_VOL_ANN
    mu_daily    = ANNUAL_DRIFT / 252.0
    sigma_daily = blend_vol / math.sqrt(252.0)
    rf_daily    = RISK_FREE / 252.0

    def gbm(n, days, s0, mu, sigma):
        Z    = np.random.standard_normal((n, days))
        logs = np.cumsum((mu - 0.5 * sigma**2) + sigma * Z, axis=1)
        return s0 * np.exp(np.hstack([np.zeros((n, 1)), logs]))

    # ── Main simulation ─────────────────────────────────────
    paths  = gbm(N_PATHS, HORIZON, price, mu_daily, sigma_daily)
    finals = paths[:, -1]

    def pct(p): return float(np.percentile(finals, p))
    def prob(cond): return round(100.0 * float(np.mean(cond)), 2)

    expected = float(np.mean(finals))
    median_p = float(np.median(finals))

    p1,p5,p10,p25 = pct(1), pct(5), pct(10), pct(25)
    p75,p90,p95,p99 = pct(75), pct(90), pct(95), pct(99)

    key_high = round(price * 1.06 / 500) * 500
    key_low  = round(price * 0.94 / 500) * 500

    probs = [
        ("Price rises from today",                   None,             prob(finals > price),          "bull"),
        ("Price falls from today",                   None,             prob(finals < price),          "bear"),
        (f"+2% gain  (≥ ₹{round(price*1.02):,})",   round(price*1.02), prob(finals >= price*1.02),   "bull"),
        (f"-2% loss  (≤ ₹{round(price*0.98):,})",   round(price*0.98), prob(finals <= price*0.98),   "bear"),
        (f"+5% gain  (≥ ₹{round(price*1.05):,})",   round(price*1.05), prob(finals >= price*1.05),   "bull"),
        (f"-5% loss  (≤ ₹{round(price*0.95):,})",   round(price*0.95), prob(finals <= price*0.95),   "bear"),
        (f"+10% gain (≥ ₹{round(price*1.10):,})",  round(price*1.10), prob(finals >= price*1.10),   "bull"),
        (f"-10% loss (≤ ₹{round(price*0.90):,})",  round(price*0.90), prob(finals <= price*0.90),   "bear"),
        (f"Above ₹{key_high:,} (resistance)",        key_high,          prob(finals >  key_high),     "bull"),
        (f"Below ₹{key_low:,}  (support)",           key_low,           prob(finals <  key_low),      "bear"),
    ]

    # Sample paths for chart (200 paths so HTML isn't huge)
    idx_s        = np.random.choice(N_PATHS, 200, replace=False)
    sample_paths = paths[idx_s, :].tolist()

    # Histogram
    counts, edges = np.histogram(finals, bins=60)
    hist_x = [round((edges[i]+edges[i+1])/2, 1) for i in range(len(counts))]
    hist_y = counts.tolist()

    # ── Options (risk-neutral GBM) ──────────────────────────
    print("  Pricing options (100,000 paths)...")
    disc    = math.exp(-rf_daily * T_DAYS)
    opt_p   = gbm(OPT_PATHS, T_DAYS, price, rf_daily, sigma_daily)
    S_T     = opt_p[:, -1]
    mc_call = float(np.mean(np.maximum(S_T - STRIKE, 0)) * disc)
    mc_put  = float(np.mean(np.maximum(STRIKE - S_T, 0)) * disc)

    # Black-Scholes
    sv, ty = blend_vol, T_DAYS / 252.0
    if sv > 0 and ty > 0:
        d1      = (math.log(price/STRIKE) + (RISK_FREE + 0.5*sv**2)*ty) / (sv*math.sqrt(ty))
        d2      = d1 - sv*math.sqrt(ty)
        bs_call = price*norm.cdf(d1) - STRIKE*math.exp(-RISK_FREE*ty)*norm.cdf(d2)
        bs_put  = STRIKE*math.exp(-RISK_FREE*ty)*norm.cdf(-d2) - price*norm.cdf(-d1)
    else:
        bs_call = bs_put = 0.0

    # Greeks (numerical MC)
    dS = price * 0.005
    def _c(s0):
        p2 = gbm(4000, T_DAYS, s0, rf_daily, sigma_daily)
        return float(np.mean(np.maximum(p2[:,-1]-STRIKE,0)) * disc)

    c0, c_up, c_dn = mc_call, _c(price+dS), _c(price-dS)
    delta = (c_up - c_dn) / (2*dS)
    gamma = (c_up - 2*c0 + c_dn) / (dS**2)

    p_t1  = gbm(4000, max(T_DAYS-1,1), price, rf_daily, sigma_daily)
    c_t1  = float(np.mean(np.maximum(p_t1[:,-1]-STRIKE,0)) * math.exp(-rf_daily*(T_DAYS-1)))
    theta = c_t1 - c0

    p_v   = gbm(4000, T_DAYS, price, rf_daily, sigma_daily*1.01)
    c_v   = float(np.mean(np.maximum(p_v[:,-1]-STRIKE,0)) * disc)
    vega  = (c_v - c0) / (sigma_daily * 0.01)

    # ── Recommendation ──────────────────────────────────────
    prob_rise  = prob(finals > price)
    prob_above = prob(finals > STRIKE)
    prob_below = prob(finals < STRIKE)

    if vix < 15:
        rec, rec_col = "⚡ BUY CALL", "#00ff88"
        rec_detail   = (
            f"VIX={vix:.1f}% is LOW → options premiums are CHEAP. "
            f"{prob_above:.0f}% probability NIFTY finishes above ₹{STRIKE:,} in 30 days. "
            f"Strategy: Buy ATM or slightly OTM calls. Risk = premium paid only."
        )
    elif vix > 22:
        rec, rec_col = "🛡 BUY PUT / HEDGE", "#ff4444"
        rec_detail   = (
            f"VIX={vix:.1f}% is ELEVATED → market pricing in FEAR. "
            f"{prob_below:.0f}% probability of decline below ₹{STRIKE:,}. "
            f"Strategy: Buy protective puts as downside hedge, or directional put trade. "
            f"Avoid naked call selling in high-VIX environment."
        )
    elif prob_rise > 60:
        rec, rec_col = "📈 BUY CALL SPREAD", "#00cfff"
        rec_detail   = (
            f"VIX={vix:.1f}% is MODERATE with bullish tilt. "
            f"{prob_above:.0f}% chance above ₹{STRIKE:,} strike. "
            f"Strategy: Bull call spread — Buy ₹{STRIKE:,} Call + Sell ₹{STRIKE+500:,} Call. "
            f"Reduces premium cost while targeting the upside move."
        )
    else:
        rec, rec_col = "🔄 SELL IRON CONDOR", "#ffaa00"
        rec_detail   = (
            f"VIX={vix:.1f}%, market appears RANGEBOUND. "
            f"Strategy: Sell OTM call + OTM put (iron condor). "
            f"Theta={theta:.2f}₹/day works in your favour. "
            f"Manage position if NIFTY moves more than ₹{round(price*0.03):,} from current level."
        )

    print(f"  ✓ Simulation done. Expected=₹{expected:,.0f}  P5=₹{p5:,.0f}  P95=₹{p95:,.0f}  Signal={rec}")

    return {
        "expected": round(expected,1), "median": round(median_p,1),
        "p1": round(p1,1),  "p5": round(p5,1),   "p10": round(p10,1),
        "p25":round(p25,1), "p75":round(p75,1),   "p90": round(p90,1),
        "p95":round(p95,1), "p99":round(p99,1),
        "probs":       probs,
        "sample_paths":[[round(v,2) for v in r] for r in sample_paths],
        "hist_x":      hist_x,
        "hist_y":      hist_y,
        "mc_call":     round(mc_call,2),   "mc_put":  round(mc_put,2),
        "bs_call":     round(bs_call,2),   "bs_put":  round(bs_put,2),
        "delta":       round(delta,4),     "gamma":   round(gamma,6),
        "theta":       round(theta,2),     "vega":    round(vega,2),
        "blend_vol":   round(blend_vol*100,2),
        "sigma_daily": round(sigma_daily*100,4),
        "mu_daily":    round(mu_daily*100,5),
        "recommendation": rec,
        "rec_color":      rec_col,
        "rec_detail":     rec_detail,
    }


# ─────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────
def fmt_vol(v):
    if v >= 10_000_000: return f"{v/10_000_000:.2f} Cr"
    if v >= 100_000:    return f"{v/100_000:.2f} L"
    return f"{v:,}"

def fmt_mcap(v):
    if not v: return "N/A"
    if v >= 1e12: return f"₹{v/1e12:.2f}T"
    if v >= 1e9:  return f"₹{v/1e9:.1f}B"
    return f"₹{v/1e6:.0f}M"


# ─────────────────────────────────────────────────────────────
#  STEP 3 — BUILD SELF-REFRESHING HTML
# ─────────────────────────────────────────────────────────────
def build_html(mkt, sim, fetch_time):
    n     = mkt["nifty"]
    price = n["price"]
    vix   = mkt["vix"]
    up    = n["day_pct"] >= 0
    days  = list(range(HORIZON + 1))
    nb    = mkt["niftybank"]
    nb_up = nb["day_pct"] >= 0

    # ── Stock rows ──────────────────────────────────────────
    stock_rows_html = ""
    for s in mkt["stocks"]:
        c = "#00ff88" if s["pct"] >= 0 else "#ff4444"
        stock_rows_html += f"""<tr>
  <td style="color:#00cfff;font-weight:bold">{s['ticker']}</td>
  <td style="color:#ddd">{s['name']}</td>
  <td style="text-align:right;color:#eee">₹{s['price']:,.2f}</td>
  <td style="text-align:right;color:{c};font-weight:bold">{s['pct']:+.2f}%</td>
  <td style="text-align:right;color:{c}">{s['change']:+.2f}</td>
  <td style="text-align:right;color:#aaa">{fmt_vol(s['volume'])}</td>
  <td style="text-align:right;color:#888">₹{s['high52']:,.0f}</td>
  <td style="text-align:right;color:#888">₹{s['low52']:,.0f}</td>
  <td style="text-align:right;color:#aaa">{s['pe'] if s['pe'] else '—'}</td>
  <td style="text-align:right;color:#aaa">{fmt_mcap(s['mcap'])}</td>
</tr>"""

    # ── Probability rows ───────────────────────────────────
    prob_rows_html = ""
    for name, target, pct_val, side in sim["probs"]:
        col = "#00ff88" if side == "bull" else "#ff4444"
        bg  = "rgba(0,255,136,0.04)" if side == "bull" else "rgba(255,68,68,0.04)"
        tgt = f"₹{target:,}" if target else "—"
        bw  = min(pct_val, 100)
        prob_rows_html += f"""<tr class="pr" style="background:{bg}">
  <td style="color:#ccc">{name}</td>
  <td style="text-align:center;color:#aaa">{tgt}</td>
  <td style="text-align:center;font-weight:bold;font-size:15px;color:{col}">{pct_val}%</td>
  <td><div style="background:#0d1825;border-radius:3px;height:9px;overflow:hidden">
    <div style="width:{bw}%;height:100%;background:{col};border-radius:3px"></div>
  </div></td>
</tr>"""

    # ── Percentile rows ────────────────────────────────────
    perc_rows_html = ""
    for pk, pv in [("P1",sim["p1"]),("P5",sim["p5"]),("P10",sim["p10"]),
                   ("P25",sim["p25"]),("Median",sim["median"]),
                   ("Mean",sim["expected"]),("P75",sim["p75"]),
                   ("P90",sim["p90"]),("P95",sim["p95"]),("P99",sim["p99"])]:
        chg  = round((pv/price-1)*100, 2)
        col  = "#00ff88" if chg >= 0 else "#ff4444"
        bold = "font-weight:bold;" if pk in ("Mean","Median") else ""
        perc_rows_html += f"""<tr>
  <td style="color:#aaa;{bold}">{pk}</td>
  <td style="color:#eee;{bold}">₹{pv:,.1f}</td>
  <td style="color:{col};font-weight:bold">{'+' if chg>=0 else ''}{chg}%</td>
</tr>"""

    # ── VIX label & bar ────────────────────────────────────
    vix_lbl  = ("LOW — options cheap" if vix < 15
                else "MODERATE — fair pricing" if vix < 22
                else "HIGH — elevated fear")
    vix_col  = "#00ff88" if vix < 15 else "#ffaa00" if vix < 22 else "#ff4444"
    vix_bar  = min(vix / 35 * 100, 100)

    # ── Tape items ─────────────────────────────────────────
    tape_items = [
        ("NIFTY 50",     f"₹{price:,.2f}",                             "neu"),
        ("CHANGE",       f"{n['day_pct']:+.2f}%  ({n['day_change']:+.2f})", "up" if up else "dn"),
        ("OPEN",         f"₹{n['open']:,.2f}",                         "neu"),
        ("HIGH",         f"₹{n['high']:,.2f}",                         "up"),
        ("LOW",          f"₹{n['low']:,.2f}",                          "dn"),
        ("VOLUME",       fmt_vol(n['volume']),                         "neu"),
        ("PREV CLOSE",   f"₹{n['prev_close']:,.2f}",                   "neu"),
        ("52W HIGH",     f"₹{n['wk52_high']:,.2f}",                    "up"),
        ("52W LOW",      f"₹{n['wk52_low']:,.2f}",                     "dn"),
        ("P/E RATIO",    str(n['pe_ratio']),                           "neu"),
        ("INDIA VIX",    f"{vix:.2f}%",                                "dn" if vix > 20 else "up"),
        ("NIFTY BANK",   f"₹{nb['price']:,.2f}  ({nb['day_pct']:+.2f}%)", "up" if nb_up else "dn"),
        ("USD/INR",      f"₹{mkt['usdinr']:.2f}",                     "neu"),
        ("REALISED VOL", f"{n['realised_vol']:.2f}%",                  "neu"),
        ("BLEND VOL",    f"{sim['blend_vol']:.2f}%",                   "neu"),
        ("MC CALL",      f"₹{sim['mc_call']:,.2f}",                    "up"),
        ("MC PUT",       f"₹{sim['mc_put']:,.2f}",                     "dn"),
        ("BS CALL",      f"₹{sim['bs_call']:,.2f}",                    "up"),
        ("EXPECTED D30", f"₹{sim['expected']:,.0f}",                   "neu"),
        ("P5 → P95",     f"₹{sim['p5']:,.0f} → ₹{sim['p95']:,.0f}",   "neu"),
        ("DELTA",        str(sim['delta']),                            "neu"),
        ("THETA/DAY",    str(sim['theta']),                            "dn"),
        ("SIGNAL",       sim['recommendation'].replace("⚡","").replace("📈","").replace("🛡","").replace("🔄","").strip(), "up"),
        ("NEXT REFRESH", f"{REFRESH_SECONDS}s",                        "neu"),
    ]
    tape_html = "".join(
        f'<span class="ti"><span class="tl">{l} </span><span class="tv {c}">{v}</span></span>'
        for l, v, c in tape_items
    ) * 2   # duplicate for seamless infinite scroll

    # ── JSON data for JS charts ────────────────────────────
    j_candle_dates  = json.dumps([d["date"]   for d in n["candles"]])
    j_candle_open   = json.dumps([d["open"]   for d in n["candles"]])
    j_candle_high   = json.dumps([d["high"]   for d in n["candles"]])
    j_candle_low    = json.dumps([d["low"]    for d in n["candles"]])
    j_candle_close  = json.dumps([d["close"]  for d in n["candles"]])
    j_candle_vol    = json.dumps([d["volume"] for d in n["candles"]])
    j_vix           = json.dumps(mkt["vix_series"])
    j_paths         = json.dumps(sim["sample_paths"])
    j_days          = json.dumps(days)
    j_hist_x        = json.dumps(sim["hist_x"])
    j_hist_y        = json.dumps(sim["hist_y"])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="{REFRESH_SECONDS}">
<title>NIFTY 50 Live — {fetch_time}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{--bg:#050A0F;--bg1:#080f18;--bg2:#0d1825;--bd:#1a3a55;
      --cy:#00cfff;--gr:#00ff88;--rd:#ff4444;--am:#ffaa00;--tx:#e0e0e0;--mu:#667788}}
body{{background:var(--bg);color:var(--tx);font-family:'Courier New',monospace;font-size:13px}}
/* header */
.hdr{{padding:14px 20px 0;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}}
.logo{{color:var(--cy);font-size:19px;font-weight:bold;letter-spacing:3px}}
.badge-live{{background:var(--rd);color:white;padding:3px 10px;border-radius:3px;font-size:11px;font-weight:bold;animation:blink 1s step-end infinite}}
@keyframes blink{{50%{{opacity:0.3}}}}
.cd{{color:var(--am);font-size:12px;margin-top:3px}}
/* tape */
.tape{{background:#0a1520;border-top:1px solid var(--bd);border-bottom:1px solid var(--bd);padding:7px 0;overflow:hidden;white-space:nowrap;margin-top:10px}}
.tape-inner{{display:inline-flex;gap:32px;animation:scroll 50s linear infinite}}
@keyframes scroll{{0%{{transform:translateX(0)}}100%{{transform:translateX(-50%)}}}}
.ti{{display:inline-block;white-space:nowrap;font-size:12px}}
.tl{{color:var(--mu)}} .tv{{font-weight:bold}}
.up{{color:var(--gr)}} .dn{{color:var(--rd)}} .neu{{color:var(--cy)}}
/* hero */
.hero{{display:flex;align-items:flex-end;gap:20px;padding:14px 20px 8px;flex-wrap:wrap}}
.pm{{font-size:54px;font-weight:bold;font-family:'Courier New',monospace}}
.pc{{font-size:20px;font-weight:bold;margin-bottom:10px}}
.meta{{color:var(--mu);font-size:12px;line-height:2}}
/* layout */
.sec{{background:var(--bg1);border:1px solid var(--bd);border-radius:6px;padding:16px;margin:8px 16px}}
.g2{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.g3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}}
.g4{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}
.g6{{display:grid;grid-template-columns:repeat(6,1fr);gap:10px}}
/* cards */
.mc{{background:var(--bg2);border:1px solid var(--bd);border-radius:6px;padding:14px;text-align:center}}
.mv{{font-size:22px;font-weight:bold;color:var(--cy);margin:6px 0}}
.ml{{font-size:10px;color:var(--mu);letter-spacing:1px;text-transform:uppercase}}
.ms{{font-size:11px;color:#778;margin-top:3px}}
h2{{color:var(--cy);font-size:13px;letter-spacing:2px;border-bottom:1px solid var(--bd);padding-bottom:8px;margin-bottom:12px}}
table{{width:100%;border-collapse:collapse}}
th{{background:#0d2035;color:var(--cy);padding:9px 12px;text-align:left;font-size:11px;letter-spacing:1px}}
td{{padding:8px 12px;border-bottom:1px solid #0b1620}}
tr:hover td{{background:rgba(0,207,255,0.05)}}
.pr:hover td{{background:rgba(0,207,255,0.07)!important}}
.vt{{background:#0d1825;border-radius:4px;height:8px;margin:4px 0;overflow:hidden}}
.vf{{height:100%;border-radius:4px;background:linear-gradient(90deg,#00ff88 0%,#ffaa00 50%,#ff4444 100%)}}
.rec-box{{border-radius:8px;padding:20px;border-width:2px;border-style:solid}}
.ra{{font-size:26px;font-weight:bold;letter-spacing:3px}}
.rd{{margin-top:10px;color:#bbb;line-height:1.7;font-size:13px}}
.gk{{background:var(--bg2);border:1px solid var(--bd);border-radius:6px;padding:12px;text-align:center}}
.gv{{font-size:20px;font-weight:bold;color:var(--am)}}
.gl{{font-size:10px;color:var(--mu);letter-spacing:1px;margin-top:4px}}
::-webkit-scrollbar{{width:4px}}::-webkit-scrollbar-track{{background:#0a1520}}::-webkit-scrollbar-thumb{{background:#1a3a55}}
@media(max-width:1100px){{.g6{{grid-template-columns:1fr 1fr 1fr}}}}
@media(max-width:800px){{.g2,.g3,.g4,.g6{{grid-template-columns:1fr 1fr}}}}
@media(max-width:480px){{.g2,.g3,.g4,.g6{{grid-template-columns:1fr}}}}
</style>
</head>
<body>

<!-- HEADER -->
<div class="hdr">
  <div>
    <div class="logo">⬡ NIFTY 50 LIVE MONTE CARLO TERMINAL</div>
    <div style="color:var(--mu);font-size:11px;margin-top:4px">
      yfinance data · Last fetched: <b style="color:var(--cy)">{fetch_time}</b>
      &nbsp;·&nbsp; Auto-refresh every <b style="color:var(--am)">{REFRESH_SECONDS}s</b>
    </div>
  </div>
  <div style="text-align:right">
    <span class="badge-live">● LIVE</span>
    <div class="cd">Next refresh: <span id="cd">{REFRESH_SECONDS}</span>s</div>
  </div>
</div>

<!-- TICKER TAPE -->
<div class="tape"><div class="tape-inner">{tape_html}</div></div>

<!-- PRICE HERO -->
<div class="hero">
  <div class="pm" style="color:{'var(--gr)' if up else 'var(--rd)'}">₹{price:,.2f}</div>
  <div>
    <div class="pc" style="color:{'var(--gr)' if up else 'var(--rd)'}">
      {n['day_pct']:+.2f}% &nbsp;({n['day_change']:+.2f})
    </div>
    <div class="meta">
      O: ₹{n['open']:,.2f} &nbsp;|&nbsp;
      H: <span class="up">₹{n['high']:,.2f}</span> &nbsp;|&nbsp;
      L: <span class="dn">₹{n['low']:,.2f}</span> &nbsp;|&nbsp;
      Prev: ₹{n['prev_close']:,.2f} &nbsp;|&nbsp;
      Vol: {fmt_vol(n['volume'])}<br>
      52W H: <span class="up">₹{n['wk52_high']:,.2f}</span> &nbsp;|&nbsp;
      52W L: <span class="dn">₹{n['wk52_low']:,.2f}</span> &nbsp;|&nbsp;
      P/E: {n['pe_ratio']} &nbsp;|&nbsp;
      Realised Vol: {n['realised_vol']:.2f}% &nbsp;|&nbsp;
      Mkt Cap: {fmt_mcap(n['mkt_cap'])}
    </div>
  </div>
  <div style="margin-left:auto;text-align:right">
    <div style="font-size:15px;font-weight:bold;padding:8px 18px;border-radius:5px;
      background:{'rgba(0,255,136,0.1)' if up else 'rgba(255,68,68,0.1)'};
      border:1px solid {'var(--gr)' if up else 'var(--rd)'};
      color:{'var(--gr)' if up else 'var(--rd)'}">
      {'▲ BULLISH' if up else '▼ BEARISH'}
    </div>
    <div style="margin-top:8px;color:var(--mu);font-size:11px;text-align:right">
      {((price/n['wk52_low']-1)*100):.1f}% above 52W Low &nbsp;|&nbsp;
      {((1-price/n['wk52_high'])*100):.1f}% below 52W High
    </div>
  </div>
</div>

<!-- SECTION A: MARKET OVERVIEW CARDS -->
<div class="sec">
  <h2>▸ MARKET OVERVIEW</h2>
  <div class="g6">
    <div class="mc">
      <div class="ml">India VIX</div>
      <div class="mv" style="color:{vix_col}">{vix:.2f}%</div>
      <div class="vt"><div class="vf" style="width:{vix_bar:.0f}%"></div></div>
      <div class="ms">{vix_lbl}</div>
    </div>
    <div class="mc">
      <div class="ml">NIFTY Bank</div>
      <div class="mv" style="color:{'var(--gr)' if nb_up else 'var(--rd)'}">₹{nb['price']:,.0f}</div>
      <div class="ms" style="color:{'var(--gr)' if nb_up else 'var(--rd)'}">{nb['day_pct']:+.2f}% today</div>
    </div>
    <div class="mc">
      <div class="ml">USD / INR</div>
      <div class="mv">₹{mkt['usdinr']:.2f}</div>
      <div class="ms">Exchange rate</div>
    </div>
    <div class="mc">
      <div class="ml">Blended Vol</div>
      <div class="mv" style="color:var(--am)">{sim['blend_vol']:.2f}%</div>
      <div class="ms">70% VIX + 30% Historical</div>
    </div>
    <div class="mc">
      <div class="ml">Expected (Day 30)</div>
      <div class="mv" style="color:var(--gr)">₹{sim['expected']:,.0f}</div>
      <div class="ms">{((sim['expected']/price-1)*100):+.2f}% from today</div>
    </div>
    <div class="mc">
      <div class="ml">P5 → P95 Band</div>
      <div class="mv" style="font-size:14px">₹{sim['p5']:,.0f}–{sim['p95']:,.0f}</div>
      <div class="ms">90% confidence range</div>
    </div>
  </div>
</div>

<!-- CHARTS ROW 1: Candlestick + VIX -->
<div class="g2" style="margin:0 16px;gap:12px">
  <div class="sec" style="margin:0">
    <h2>▸ 30-DAY OHLCV CANDLESTICK CHART</h2>
    <div id="ch-candle" style="height:350px"></div>
  </div>
  <div class="sec" style="margin:0">
    <h2>▸ INTRADAY INDIA VIX  <span style="color:var(--mu);font-size:10px">Today · 1-min intervals</span></h2>
    <div id="ch-vix" style="height:350px"></div>
  </div>
</div>

<!-- CHARTS ROW 2: MC Paths + Confidence Bands -->
<div class="g2" style="margin:8px 16px 0;gap:12px">
  <div class="sec" style="margin:0">
    <h2>▸ MONTE CARLO PATHS  <span style="color:var(--mu);font-size:10px">200 of 10,000 · 30 days</span></h2>
    <div id="ch-paths" style="height:340px"></div>
  </div>
  <div class="sec" style="margin:0">
    <h2>▸ CONFIDENCE BANDS  <span style="color:var(--mu);font-size:10px">P5 · P25 · Mean · P75 · P95</span></h2>
    <div id="ch-bands" style="height:340px"></div>
  </div>
</div>

<!-- HISTOGRAM -->
<div class="sec">
  <h2>▸ RETURN DISTRIBUTION AT DAY 30  <span style="color:var(--mu);font-size:10px">Green = above today · Red = below</span></h2>
  <div id="ch-hist" style="height:300px"></div>
</div>

<!-- TOP STOCKS TABLE -->
<div class="sec">
  <h2>▸ TOP 10 NIFTY CONSTITUENTS  <span style="color:var(--mu);font-size:10px">Live · refreshes every {REFRESH_SECONDS}s</span></h2>
  <div style="overflow-x:auto">
    <table>
      <thead><tr>
        <th>Ticker</th><th>Name</th>
        <th style="text-align:right">Price</th><th style="text-align:right">Chg %</th>
        <th style="text-align:right">Chg ₹</th><th style="text-align:right">Volume</th>
        <th style="text-align:right">52W H</th><th style="text-align:right">52W L</th>
        <th style="text-align:right">P/E</th><th style="text-align:right">Mkt Cap</th>
      </tr></thead>
      <tbody>{stock_rows_html}</tbody>
    </table>
  </div>
</div>

<!-- PROBABILITY GRID -->
<div class="sec">
  <h2>▸ PROBABILITY GRID  
    <span style="display:inline-block;padding:2px 8px;border-radius:10px;font-size:10px;background:rgba(0,255,136,0.12);color:#00ff88;border:1px solid #00ff88;margin-left:6px">BULL</span>
    <span style="display:inline-block;padding:2px 8px;border-radius:10px;font-size:10px;background:rgba(255,68,68,0.12);color:#ff4444;border:1px solid #ff4444;margin-left:4px">BEAR</span>
  </h2>
  <table>
    <thead><tr>
      <th>Scenario</th><th style="text-align:center">Target</th>
      <th style="text-align:center">Probability</th><th>Bar</th>
    </tr></thead>
    <tbody>{prob_rows_html}</tbody>
  </table>
</div>

<!-- SIMULATION RESULTS + OPTIONS -->
<div class="g2" style="margin:0 16px;gap:12px">
  <div class="sec" style="margin:0">
    <h2>▸ PERCENTILE TABLE  <span style="color:var(--mu);font-size:10px">Day 30 outcomes from {N_PATHS:,} paths</span></h2>
    <table>
      <thead><tr><th>Percentile</th><th>Price (₹)</th><th>vs Today</th></tr></thead>
      <tbody>{perc_rows_html}</tbody>
    </table>
  </div>
  <div class="sec" style="margin:0">
    <h2>▸ OPTIONS PRICING  <span style="color:var(--mu);font-size:10px">Strike ₹{STRIKE:,} · {T_DAYS}d · Vol {sim['blend_vol']:.2f}%</span></h2>
    <div class="g2" style="margin-bottom:14px">
      <div class="mc"><div class="ml">MC Call</div>
        <div class="mv up">₹{sim['mc_call']:,.2f}</div><div class="ms">100k paths</div></div>
      <div class="mc"><div class="ml">BS Call</div>
        <div class="mv neu">₹{sim['bs_call']:,.2f}</div><div class="ms">Analytical</div></div>
      <div class="mc"><div class="ml">MC Put</div>
        <div class="mv dn">₹{sim['mc_put']:,.2f}</div><div class="ms">100k paths</div></div>
      <div class="mc"><div class="ml">BS Put</div>
        <div class="mv" style="color:var(--am)">₹{sim['bs_put']:,.2f}</div>
        <div class="ms">Analytical</div></div>
    </div>
    <div style="font-size:10px;color:var(--mu);letter-spacing:1px;margin-bottom:8px">GREEKS (CALL)</div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">
      <div class="gk"><div class="gv">{sim['delta']:.4f}</div><div class="gl">Delta Δ</div></div>
      <div class="gk"><div class="gv">{sim['gamma']:.6f}</div><div class="gl">Gamma Γ</div></div>
      <div class="gk"><div class="gv">{sim['theta']:.2f}</div><div class="gl">Theta Θ/day</div></div>
      <div class="gk"><div class="gv">{sim['vega']:.2f}</div><div class="gl">Vega ν</div></div>
    </div>
    <div style="margin-top:12px;padding:10px;background:var(--bg2);border-radius:6px;border:1px solid var(--bd);font-size:11px;color:#aaa">
      MC vs BS — Call diff: ₹{abs(sim['mc_call']-sim['bs_call']):.2f} &nbsp;·&nbsp;
      Put diff: ₹{abs(sim['mc_put']-sim['bs_put']):.2f} &nbsp;·&nbsp;
      Put-Call parity (MC): ₹{sim['mc_call']-sim['mc_put']:,.2f} &nbsp;·&nbsp;
      Moneyness: {'OTM' if price < STRIKE else 'ITM'} ({((price/STRIKE-1)*100):+.1f}%)
    </div>
  </div>
</div>

<!-- RECOMMENDATION -->
<div class="sec">
  <h2>▸ TRADING RECOMMENDATION  <span style="color:var(--mu);font-size:10px">Based on VIX + Monte Carlo probabilities</span></h2>
  <div class="rec-box" style="border-color:{sim['rec_color']};background:rgba(0,0,0,0.25)">
    <div class="ra" style="color:{sim['rec_color']}">{sim['recommendation']}</div>
    <div class="rd">{sim['rec_detail']}</div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:14px">
      <div style="padding:10px;background:var(--bg2);border-radius:6px;border:1px solid var(--bd)">
        <div style="color:var(--mu);font-size:10px;letter-spacing:1px">STRIKE / EXPIRY</div>
        <div style="color:var(--cy);font-size:16px;font-weight:bold;margin-top:4px">₹{STRIKE:,}  ·  {T_DAYS}d</div>
      </div>
      <div style="padding:10px;background:var(--bg2);border-radius:6px;border:1px solid var(--bd)">
        <div style="color:var(--mu);font-size:10px;letter-spacing:1px">DAILY 1-SIGMA MOVE</div>
        <div style="color:var(--am);font-size:16px;font-weight:bold;margin-top:4px">
          ±₹{round(sim['sigma_daily']/100*price):,}  ({sim['sigma_daily']:.3f}%)
        </div>
      </div>
      <div style="padding:10px;background:var(--bg2);border-radius:6px;border:1px solid var(--bd)">
        <div style="color:var(--mu);font-size:10px;letter-spacing:1px">NEXT DATA REFRESH</div>
        <div style="color:var(--am);font-size:16px;font-weight:bold;margin-top:4px" id="cd2">{REFRESH_SECONDS}s</div>
      </div>
    </div>
    <div style="margin-top:12px;padding:10px;background:#050A0F;border-left:3px solid var(--am);color:#aaa;font-size:11px;line-height:1.8">
      <b style="color:var(--am)">⚠ RISK WARNING:</b> GBM model assumes log-normal returns and constant volatility.
      Does NOT capture fat tails, jumps, or regime changes. This is <b style="color:var(--rd)">NOT investment advice</b>.
      Always use stop-losses. Size positions appropriately. Past simulation results do not guarantee future outcomes.
    </div>
  </div>
</div>

<!-- FOOTER -->
<div style="text-align:center;color:#334;padding:16px;font-size:11px;border-top:1px solid var(--bd);margin-top:8px">
  NIFTY 50 Live Monte Carlo Terminal &nbsp;·&nbsp; Python + yfinance + Plotly &nbsp;·&nbsp;
  Fetched: {fetch_time} &nbsp;·&nbsp; Refreshes in <span id="cd3">{REFRESH_SECONDS}</span>s &nbsp;·&nbsp;
  <span style="color:var(--rd)">NOT INVESTMENT ADVICE</span>
</div>

<script>
// ── Countdown ─────────────────────────────────────────────
let _s = {REFRESH_SECONDS};
setInterval(()=>{{
  _s = Math.max(0, _s-1);
  ['cd','cd2','cd3'].forEach(id=>{{ const e=document.getElementById(id); if(e) e.textContent=_s+'s'; }});
}}, 1000);

// ── Plotly base layout ─────────────────────────────────────
const BG='#050A0F', G='#0d1e30', F='#99aabb';
const L = {{
  paper_bgcolor:BG, plot_bgcolor:BG,
  font:{{color:F,family:'Courier New',size:11}},
  margin:{{t:20,b:45,l:65,r:20}},
  xaxis:{{gridcolor:G,zerolinecolor:G,color:F}},
  yaxis:{{gridcolor:G,zerolinecolor:G,color:F,tickformat:',.0f'}},
}};
const CFG = {{responsive:true,displayModeBar:false}};
const spot = {price};

// ── 1. Candlestick chart ──────────────────────────────────
(()=>{{
  const dates={j_candle_dates}, o={j_candle_open}, h={j_candle_high},
        lo={j_candle_low}, c={j_candle_close}, v={j_candle_vol};
  if(!dates.length){{ document.getElementById('ch-candle').innerHTML=
    '<div style="padding:60px;text-align:center;color:#334">No data</div>'; return; }}

  const candle = {{
    type:'candlestick', x:dates, open:o, high:h, low:lo, close:c, name:'NIFTY 50',
    increasing:{{line:{{color:'#00ff88'}},fillcolor:'rgba(0,255,136,0.45)'}},
    decreasing:{{line:{{color:'#ff4444'}},fillcolor:'rgba(255,68,68,0.45)'}},
    yaxis:'y'
  }};
  const vol = {{
    type:'bar', x:dates, y:v, name:'Volume', showlegend:false,
    marker:{{color:c.map((cl,i)=>cl>=o[i]?'rgba(0,255,136,0.28)':'rgba(255,68,68,0.28)')}},
    yaxis:'y2'
  }};
  Plotly.newPlot('ch-candle', [candle,vol], Object.assign({{}},L,{{
    height:340,
    yaxis: Object.assign({{}},L.yaxis,{{title:'Price (₹)',domain:[0.28,1]}}),
    yaxis2:{{gridcolor:G,zerolinecolor:G,color:F,title:'',domain:[0,0.23],showticklabels:false}},
    xaxis: Object.assign({{}},L.xaxis,{{rangeslider:{{visible:false}}}}),
    legend:{{bgcolor:'rgba(0,0,0,0)',font:{{size:10}}}}
  }}), CFG);
}})();

// ── 2. VIX intraday ──────────────────────────────────────
(()=>{{
  const vd={j_vix};
  if(!vd.length){{ document.getElementById('ch-vix').innerHTML=
    '<div style="padding:60px;text-align:center;color:#334">VIX data unavailable</div>'; return; }}
  const xs=vd.map((_,i)=>i);
  const last=vd[vd.length-1];
  const col=last>20?'#ff4444':last>15?'#ffaa00':'#00ff88';
  const fc=col.replace('#','').match(/../g).map(x=>parseInt(x,16));
  Plotly.newPlot('ch-vix',[
    {{ x:xs,y:vd,mode:'lines',fill:'tozeroy',
       line:{{color:col,width:2}},
       fillcolor:`rgba(${{fc[0]}},${{fc[1]}},${{fc[2]}},0.1)`,
       name:'India VIX',
       hovertemplate:'Min %{{x}}<br>VIX: %{{y:.2f}}%<extra></extra>' }},
    {{ x:[0,xs[xs.length-1]],y:[20,20],mode:'lines',
       line:{{color:'#ff4444',width:1,dash:'dot'}},name:'20 — Fear threshold' }},
    {{ x:[0,xs[xs.length-1]],y:[15,15],mode:'lines',
       line:{{color:'#ffaa00',width:1,dash:'dot'}},name:'15 — Caution level' }}
  ], Object.assign({{}},L,{{
    height:340,
    xaxis:Object.assign({{}},L.xaxis,{{title:'Minutes into session'}}),
    yaxis:Object.assign({{}},L.yaxis,{{title:'VIX Level'}}),
    legend:{{bgcolor:'rgba(0,0,0,0)',font:{{size:10}}}}
  }}), CFG);
}})();

// ── 3. MC Sample Paths ────────────────────────────────────
(()=>{{
  const paths={j_paths}, days={j_days};
  if(!paths.length) return;
  const traces=[];
  const n=Math.min(paths.length,150);
  for(let i=0;i<n;i++){{
    traces.push({{x:days,y:paths[i],mode:'lines',
      line:{{color:'rgba(0,180,255,0.05)',width:1}},showlegend:false,hoverinfo:'skip'}});
  }}
  traces.push({{x:days,y:Array(days.length).fill(spot),mode:'lines',
    line:{{color:'rgba(255,255,255,0.35)',width:1.5,dash:'dot'}},
    name:'Spot ₹'+spot.toLocaleString()}});
  Plotly.newPlot('ch-paths',traces,Object.assign({{}},L,{{
    height:330,
    xaxis:Object.assign({{}},L.xaxis,{{title:'Trading Day'}}),
    yaxis:Object.assign({{}},L.yaxis,{{title:'Price (₹)'}}),
    legend:{{bgcolor:'rgba(0,0,0,0)',font:{{size:10}}}}
  }}), CFG);
}})();

// ── 4. Confidence Bands ───────────────────────────────────
(()=>{{
  const days={j_days}, mu={sim['mu_daily']}/100, sigma={sim['sigma_daily']}/100;
  const targets={{p5:{sim['p5']},p25:{sim['p25']},mn:{sim['expected']},p75:{sim['p75']},p95:{sim['p95']}}};

  function band(t30,darr){{
    return darr.map(d=>{{
      if(d===0) return spot;
      return spot*Math.exp((mu-0.5*sigma*sigma)*d+Math.log(t30/spot)*Math.sqrt(d/30));
    }});
  }}
  const p5c=band(targets.p5,days), p25c=band(targets.p25,days),
        mnc=band(targets.mn,days), p75c=band(targets.p75,days), p95c=band(targets.p95,days);

  Plotly.newPlot('ch-bands',[
    {{x:[...days,...[...days].reverse()],y:[...p95c,...p5c.slice().reverse()],
      fill:'toself',fillcolor:'rgba(0,180,255,0.07)',line:{{color:'transparent'}},name:'P5–P95'}},
    {{x:[...days,...[...days].reverse()],y:[...p75c,...p25c.slice().reverse()],
      fill:'toself',fillcolor:'rgba(0,180,255,0.14)',line:{{color:'transparent'}},name:'P25–P75'}},
    {{x:days,y:p5c, mode:'lines',line:{{color:'#ff4444',width:1.5,dash:'dash'}},name:'P5'}},
    {{x:days,y:p95c,mode:'lines',line:{{color:'#00ff88',width:1.5,dash:'dash'}},name:'P95'}},
    {{x:days,y:mnc, mode:'lines',line:{{color:'#00cfff',width:3}},name:'Mean'}},
    {{x:days,y:Array(days.length).fill(spot),mode:'lines',
      line:{{color:'rgba(255,255,255,0.3)',width:1,dash:'dot'}},name:'Spot',showlegend:false}}
  ], Object.assign({{}},L,{{
    height:330,
    xaxis:Object.assign({{}},L.xaxis,{{title:'Trading Day'}}),
    yaxis:Object.assign({{}},L.yaxis,{{title:'Price (₹)'}}),
    legend:{{bgcolor:'rgba(0,0,0,0)',font:{{size:10}}}},
    annotations:[{{
      x:30,y:mnc[30],text:'Expected: ₹'+Math.round(targets.mn).toLocaleString(),
      showarrow:true,arrowcolor:'#00cfff',font:{{color:'#00cfff',size:11}},
      bgcolor:'#0d1825',bordercolor:'#00cfff',borderwidth:1,ax:45,ay:-25
    }}]
  }}), CFG);
}})();

// ── 5. Histogram ──────────────────────────────────────────
(()=>{{
  const hx={j_hist_x}, hy={j_hist_y};
  Plotly.newPlot('ch-hist',[{{
    x:hx,y:hy,type:'bar',
    marker:{{color:hx.map(v=>v>=spot?'rgba(0,255,136,0.7)':'rgba(255,68,68,0.7)')}},
    name:'Distribution',
    hovertemplate:'₹%{{x:,.0f}}<br>Count: %{{y}}<extra></extra>'
  }}], Object.assign({{}},L,{{
    height:290,
    xaxis:Object.assign({{}},L.xaxis,{{title:'NIFTY 50 Price at Day 30 (₹)'}}),
    yaxis:Object.assign({{}},L.yaxis,{{title:'Frequency'}}),
    shapes:[{{type:'line',x0:spot,x1:spot,y0:0,y1:1,yref:'paper',
              line:{{color:'white',width:2,dash:'dot'}}}}],
    annotations:[{{x:spot,y:1,yref:'paper',text:'Spot ₹'+spot.toLocaleString(),
      showarrow:false,font:{{color:'white',size:11}},bgcolor:'#0d1825',yanchor:'bottom'}}]
  }}), CFG);
}})();
</script>
</body>
</html>"""
    return html


# ─────────────────────────────────────────────────────────────
#  MAIN LOOP
# ─────────────────────────────────────────────────────────────
def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║         NIFTY 50 LIVE DASHBOARD — Starting                  ║
╚══════════════════════════════════════════════════════════════╝
""")
    cycle       = 0
    browser_opened = False

    while True:
        cycle += 1
        now = datetime.now().strftime("%d-%b-%Y  %H:%M:%S")
        print(f"\n{'='*62}")
        print(f"  CYCLE {cycle}  |  {now}")
        print(f"{'='*62}")

        try:
            mkt  = fetch_all()
            sim  = run_simulation(mkt["nifty"]["price"], mkt["vix"])

            print("  Building HTML...")
            html = build_html(mkt, sim, now)
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                f.write(html)

            kb = os.path.getsize(OUTPUT_FILE) // 1024
            print(f"""
  ✅  Dashboard written: {OUTPUT_FILE}  ({kb} KB)
  ─────────────────────────────────────────────────────
  Price  : ₹{mkt['nifty']['price']:,.2f}  ({mkt['nifty']['day_pct']:+.2f}%)
  VIX    : {mkt['vix']:.2f}%  |  USD/INR: ₹{mkt['usdinr']:.2f}
  Exp D30: ₹{sim['expected']:,.0f}  |  P5: ₹{sim['p5']:,.0f}  P95: ₹{sim['p95']:,.0f}
  Call   : ₹{sim['mc_call']:.2f}  |  Put: ₹{sim['mc_put']:.2f}
  Signal : {sim['recommendation']}
  ─────────────────────────────────────────────────────""")

            # Open browser on first successful run
            if not browser_opened:
                browser_opened = True
                path = os.path.abspath(OUTPUT_FILE)
                threading.Thread(target=lambda: (time.sleep(1.5), webbrowser.open(f"file:///{path}")), daemon=True).start()
                print(f"  🌐 Opening browser: file:///{path}")

        except Exception as e:
            print(f"\n  ✗ Cycle error: {e}")
            import traceback; traceback.print_exc()

        # Countdown to next refresh
        print(f"  Next refresh in {REFRESH_SECONDS}s  (Ctrl+C to stop)\n")
        for remaining in range(REFRESH_SECONDS, 0, -1):
            print(f"  ⏳ {remaining:3d}s remaining...", end="\r")
            time.sleep(1)
        print()


if __name__ == "__main__":
    main()