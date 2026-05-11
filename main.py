"""
main.py — Main orchestrator for NIFTY 50 Two-Page Trading Terminal
Runs the data fetch + simulation + screener loop AND serves
a lightweight HTTP API for the live search / peer comparison features.

RUN:  python main.py
"""

import os
import time
import threading
import webbrowser
import json
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ── local modules ─────────────────────────────────────────────
from data_fetch   import fetch_all_dashboard, fetch_screener_batch, fetch_stock_full, NIFTY50_STOCKS
from simulation   import run_simulation
from screener     import run_screener, select_top_picks
from sentiment    import get_market_sentiment, get_stock_sentiment
from indicators   import compute_all_indicators, build_tech_summary
from fundamentals import extract_fundamentals, build_fund_table
from screener     import generate_trade_recommendation, compute_composite_score, composite_to_signal
from ui_builder   import build_page1_html, build_page2_html

# ─────────────────────────────────────────────────────────────
#  SETTINGS
# ─────────────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
OUTPUT_P1       = os.path.join(BASE_DIR, "nifty_dashboard_live.html")
OUTPUT_P2       = os.path.join(BASE_DIR, "nifty_intelligence.html")
REFRESH_SECONDS = 60
SERVER_PORT     = 8765
RUN_SENTIMENT   = True   # set False to skip news fetching for speed

# Global cache shared between HTTP server and main loop
_cache = {
    "screener":   [],
    "mkt":        {},
    "last_fetch": "Never",
}
_cache_lock = threading.Lock()


# ─────────────────────────────────────────────────────────────
#  HTTP API SERVER  (for live search + peer comparison)
# ─────────────────────────────────────────────────────────────
class APIHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # suppress access logs

    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path
        qs     = parse_qs(parsed.query)

        # ── /search?ticker=RELIANCE ─────────────────────────
        if path == "/search":
            ticker_input = (qs.get("ticker", [""])[0]).strip().upper()
            if not ticker_input:
                self._json({"error": "Missing ticker"}, 400); return

            # Normalise: add .NS if not present
            sym = ticker_input if ticker_input.endswith(".NS") else ticker_input + ".NS"
            print(f"  [API] Search request: {sym}")

            sd = fetch_stock_full(sym)
            if not sd:
                self._json({"error": f"Could not fetch data for {sym}. Try full ticker e.g. RELIANCE"}); return

            # Indicators
            hist = sd.get("h1y") if sd.get("h1y") is not None and not sd.get("h1y").empty else sd.get("h6mo")
            ind  = compute_all_indicators(hist)
            fund = extract_fundamentals(sd.get("info", {}))
            sent = get_stock_sentiment(sd.get("name",""), ticker_input)

            ts = ind.get("tech_score", 50)
            fs = fund.get("fund_score", 50)
            ss = sent.get("score", 50)
            comp = compute_composite_score(ts, fs, ss)
            signal, sig_col = composite_to_signal(comp)

            # Short-name for screener compat
            sd["short_name"] = sd.get("name", sym)
            rec = generate_trade_recommendation(sd, ind, fund, sent, "intraday")

            tech_rows = build_tech_summary(ind)
            fund_rows = build_fund_table(fund)

            # Chart series
            closes, ma20s, ma50s, rsi_series = [], [], [], []
            if hist is not None and not hist.empty:
                import numpy as np
                closes     = [round(float(x),2) for x in hist["Close"].tolist()[-120:]]
                ma20_s     = hist["Close"].rolling(20).mean().tolist()[-120:]
                ma50_s     = hist["Close"].rolling(50).mean().tolist()[-120:]
                from indicators import calc_rsi
                rsi_s      = calc_rsi(hist["Close"]).tolist()[-120:]
                ma20s  = [round(float(x),2) if x==x else None for x in ma20_s]
                ma50s  = [round(float(x),2) if x==x else None for x in ma50_s]
                rsi_series = [round(float(x),2) if x==x else None for x in rsi_s]

            sent_lbl, _ = (sent.get("label","neutral"), None)

            self._json({
                "ticker":    ticker_input,
                "name":      sd.get("name",""),
                "price":     sd.get("price", 0),
                "signal":    signal,
                "composite": comp,
                "tech_score":ts,
                "fund_score":fs,
                "sent_score":ss,
                "entry":     rec["entry"],
                "sl":        rec["stop_loss"],
                "t1":        rec["target1"],
                "t2":        rec["target2"],
                "t3":        rec["target3"],
                "rr":        rec["rr_ratio"],
                "rationale": rec["rationale"],
                "tech_rows": [[r[0],r[1],r[2],r[3]] for r in tech_rows],
                "fund_rows": [[r[0],r[1],r[2],r[3]] for r in fund_rows],
                "closes":    closes,
                "ma20":      ma20s,
                "ma50":      ma50s,
                "rsi_series":rsi_series,
                "sentiment": sent.get("label","neutral"),
                "news":      sent.get("articles",[])[:5],
            })

        # ── /peer?t=RELIANCE&t=TCS&t=INFY ──────────────────
        elif path == "/peer":
            tickers_raw = qs.get("t", [])
            if not tickers_raw:
                self._json({"error": "No tickers provided"}); return

            results = []
            for raw in tickers_raw[:5]:
                sym = raw.strip().upper()
                if not sym.endswith(".NS"):
                    sym += ".NS"
                sd = fetch_stock_full(sym)
                if not sd:
                    continue
                hist = sd.get("h1y") if sd.get("h1y") is not None and not sd.get("h1y").empty else sd.get("h6mo")
                ind  = compute_all_indicators(hist)
                fund = extract_fundamentals(sd.get("info", {}))
                sent = {"score": 50}
                ts = ind.get("tech_score", 50)
                fs = fund.get("fund_score", 50)
                comp = compute_composite_score(ts, fs, 50)
                results.append({
                    "ticker":     raw.strip().upper(),
                    "name":       sd.get("name",""),
                    "price":      sd.get("price",0),
                    "tech_score": ts,
                    "fund_score": fs,
                    "sent_score": 50,
                    "composite":  comp,
                    "fund": {
                        "pe":              fund.get("pe"),
                        "pb":              fund.get("pb"),
                        "roe":             fund.get("roe"),
                        "roce":            fund.get("roce"),
                        "eps_growth":      fund.get("eps_growth"),
                        "revenue_growth":  fund.get("revenue_growth"),
                        "debt_equity":     fund.get("debt_equity"),
                        "current_ratio":   fund.get("current_ratio"),
                        "operating_margin":fund.get("operating_margin"),
                        "net_margin":      fund.get("net_margin"),
                    }
                })
                time.sleep(0.3)

            self._json(results)

        # ── /health ─────────────────────────────────────────
        elif path == "/health":
            with _cache_lock:
                self._json({"status":"ok","last_fetch":_cache["last_fetch"],
                            "screener_count":len(_cache["screener"])})

        # ── serve HTML files ─────────────────────────────────
        elif path in ("/", "/nifty_dashboard_live.html"):
            self._serve_file(OUTPUT_P1)
        elif path == "/nifty_intelligence.html":
            self._serve_file(OUTPUT_P2)
        else:
            self.send_response(404); self.end_headers()

    def _serve_file(self, filepath):
        try:
            with open(filepath, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            self.send_response(404); self.end_headers()


def start_server():
    server = HTTPServer(("127.0.0.1", SERVER_PORT), APIHandler)
    print(f"  🌐 API server started: http://127.0.0.1:{SERVER_PORT}")
    server.serve_forever()


# ─────────────────────────────────────────────────────────────
#  MAIN LOOP
# ─────────────────────────────────────────────────────────────
def run_cycle(cycle, browser_opened):
    now = datetime.now().strftime("%d-%b-%Y  %H:%M:%S")
    print(f"\n{'='*62}")
    print(f"  CYCLE {cycle}  |  {now}")
    print(f"{'='*62}")

    # ── Page 1: Dashboard data ──────────────────────────────
    mkt = fetch_all_dashboard()
    sim = run_simulation(mkt["nifty"]["price"], mkt["vix"])

    print("  Building Page 1 HTML...")
    html1 = build_page1_html(mkt, sim, now)
    with open(OUTPUT_P1, "w", encoding="utf-8") as f:
        f.write(html1)
    kb1 = os.path.getsize(OUTPUT_P1) // 1024
    print(f"  ✅  Page 1 written: {OUTPUT_P1}  ({kb1} KB)")

    # ── Page 2: Screener + Intelligence ────────────────────
    print("\n  Running screener...")
    stock_batch = fetch_screener_batch(list(NIFTY50_STOCKS.keys())[:25])
    screener    = run_screener(stock_batch, run_sentiment=RUN_SENTIMENT)

    print("  Fetching market sentiment...")
    market_sent = get_market_sentiment()

    top_intraday, top_longterm = select_top_picks(screener)

    print("  Building Page 2 HTML...")
    html2 = build_page2_html(mkt, screener, top_intraday, top_longterm, market_sent, now)
    with open(OUTPUT_P2, "w", encoding="utf-8") as f:
        f.write(html2)
    kb2 = os.path.getsize(OUTPUT_P2) // 1024
    print(f"  ✅  Page 2 written: {OUTPUT_P2}  ({kb2} KB)")

    # Update global cache
    with _cache_lock:
        _cache["screener"]   = screener
        _cache["mkt"]        = mkt
        _cache["last_fetch"] = now

    # Print summary
    print(f"""
  ─────────────────────────────────────────────────────
  NIFTY 50 : ₹{mkt['nifty']['price']:,.2f}  ({mkt['nifty']['day_pct']:+.2f}%)
  VIX      : {mkt['vix']:.2f}%  |  USD/INR: ₹{mkt['usdinr']:.2f}
  Exp D30  : ₹{sim['expected']:,.0f}  |  P5-P95: ₹{sim['p5']:,.0f}–₹{sim['p95']:,.0f}
  Signal   : {sim['recommendation']}
  Screener : {len(screener)} stocks ranked  |  Top: {screener[0]['ticker'] if screener else 'N/A'} ({screener[0]['composite'] if screener else 0}/100)
  Intraday : {', '.join(s['ticker'] for s in top_intraday)}
  LongTerm : {', '.join(s['ticker'] for s in top_longterm)}
  ─────────────────────────────────────────────────────""")

    return browser_opened


def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║   NIFTY 50 TWO-PAGE TRADING TERMINAL — Starting                 ║
║   Page 1: MC Dashboard   |   Page 2: Stock Intelligence         ║
╚══════════════════════════════════════════════════════════════════╝
""")

    # Start API server in background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    cycle          = 0
    browser_opened = False

    while True:
        cycle += 1
        try:
            run_cycle(cycle, browser_opened)

            if not browser_opened:
                browser_opened = True
                url = f"http://127.0.0.1:{SERVER_PORT}/nifty_dashboard_live.html"
                threading.Thread(
                    target=lambda: (time.sleep(1.5), webbrowser.open(url)),
                    daemon=True
                ).start()
                print(f"  🌐 Opening browser: {url}")

        except Exception as e:
            print(f"\n  ✗ Cycle error: {e}")
            import traceback; traceback.print_exc()

        print(f"\n  Next refresh in {REFRESH_SECONDS}s  (Ctrl+C to stop)")
        for remaining in range(REFRESH_SECONDS, 0, -1):
            print(f"  ⏳ {remaining:3d}s remaining...", end="\r")
            time.sleep(1)
        print()


if __name__ == "__main__":
    main()