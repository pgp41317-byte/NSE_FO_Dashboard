"""
ui_builder.py — HTML dashboard builder for Page 1 (NIFTY MC Terminal) and Page 2 (Stock Intelligence).
"""

import json
import math

from simulation import STRIKE, T_DAYS, N_PATHS, HORIZON
from indicators import build_tech_summary, tech_score_to_signal
from fundamentals import build_fund_table
from sentiment import sentiment_label_display, sentiment_color
from screener import composite_to_signal

REFRESH_SECONDS = 60


# ─────────────────────────────────────────────────────────────
#  SHARED HELPERS
# ─────────────────────────────────────────────────────────────
def fmt_vol(v):
    if not v: return "—"
    if v >= 10_000_000: return f"{v/10_000_000:.2f} Cr"
    if v >= 100_000:    return f"{v/100_000:.2f} L"
    return f"{v:,}"

def fmt_mcap(v):
    if not v: return "N/A"
    if v >= 1e12: return f"₹{v/1e12:.2f}T"
    if v >= 1e9:  return f"₹{v/1e9:.1f}B"
    return f"₹{v/1e6:.0f}M"

def fmt_n(v, d=2, prefix=""):
    if v is None: return "N/A"
    try:
        return f"{prefix}{float(v):.{d}f}"
    except:
        return str(v)

def col(v):
    return "#00ff88" if (v or 0) >= 0 else "#ff4444"


# ─────────────────────────────────────────────────────────────
#  SHARED CSS / HEADER / TAPE
# ─────────────────────────────────────────────────────────────
SHARED_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#050A0F;--bg1:#080f18;--bg2:#0d1825;--bg3:#111f30;--bd:#1a3a55;
      --cy:#00cfff;--gr:#00ff88;--rd:#ff4444;--am:#ffaa00;--pu:#cc88ff;
      --tx:#e0e0e0;--mu:#667788;--font:'Courier New',monospace}
body{background:var(--bg);color:var(--tx);font-family:var(--font);font-size:13px;overflow-x:hidden}
.hdr{padding:12px 20px 0;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;border-bottom:1px solid var(--bd)}
.logo{color:var(--cy);font-size:17px;font-weight:bold;letter-spacing:3px}
.badge-live{background:var(--rd);color:white;padding:3px 10px;border-radius:3px;font-size:10px;font-weight:bold;animation:blink 1s step-end infinite}
@keyframes blink{50%{opacity:0.3}}
.nav{display:flex;gap:0;border:1px solid var(--bd);border-radius:4px;overflow:hidden}
.nav a{padding:7px 18px;color:var(--mu);text-decoration:none;font-size:12px;letter-spacing:1px;transition:all .2s;display:inline-block}
.nav a.active{background:var(--cy);color:#050A0F;font-weight:bold}
.nav a:hover:not(.active){background:var(--bg2);color:var(--cy)}
.index-bar{display:flex;gap:18px;padding:8px 20px;background:var(--bg1);border-bottom:1px solid var(--bd);flex-wrap:wrap}
.ib{display:flex;flex-direction:column;align-items:flex-start;gap:0}
.ib-name{font-size:9px;color:var(--mu);letter-spacing:1px}
.ib-val{font-size:13px;font-weight:bold}
.ib-chg{font-size:10px}
.tape{background:#0a1520;border-top:1px solid var(--bd);border-bottom:1px solid var(--bd);padding:7px 0;overflow:hidden;white-space:nowrap}
.tape-inner{display:inline-flex;gap:32px;animation:scroll 50s linear infinite}
@keyframes scroll{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}
.ti{display:inline-block;white-space:nowrap;font-size:12px}
.tl{color:var(--mu)} .tv{font-weight:bold}
.up{color:var(--gr)} .dn{color:var(--rd)} .neu{color:var(--cy)} .amb{color:var(--am)}
.sec{background:var(--bg1);border:1px solid var(--bd);border-radius:6px;padding:16px;margin:8px 16px}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.g3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.g6{display:grid;grid-template-columns:repeat(6,1fr);gap:10px}
.mc{background:var(--bg2);border:1px solid var(--bd);border-radius:6px;padding:14px;text-align:center}
.mv{font-size:20px;font-weight:bold;color:var(--cy);margin:6px 0}
.ml{font-size:10px;color:var(--mu);letter-spacing:1px;text-transform:uppercase}
.ms{font-size:11px;color:#778;margin-top:3px}
h2{color:var(--cy);font-size:12px;letter-spacing:2px;border-bottom:1px solid var(--bd);padding-bottom:8px;margin-bottom:12px;text-transform:uppercase}
table{width:100%;border-collapse:collapse}
th{background:#0d2035;color:var(--cy);padding:8px 10px;text-align:left;font-size:10px;letter-spacing:1px}
td{padding:7px 10px;border-bottom:1px solid #0a1620;font-size:12px}
tr:hover td{background:rgba(0,207,255,0.04)}
.score-bar{background:#0d1825;border-radius:3px;height:6px;overflow:hidden;margin-top:4px}
.score-fill{height:100%;border-radius:3px}
.card-pick{background:var(--bg2);border:1px solid var(--bd);border-radius:8px;padding:16px;
           transition:border-color .2s;cursor:default}
.card-pick:hover{border-color:var(--cy)}
.signal-badge{display:inline-block;padding:2px 10px;border-radius:10px;font-size:10px;font-weight:bold;letter-spacing:1px}
.gk{background:var(--bg2);border:1px solid var(--bd);border-radius:6px;padding:12px;text-align:center}
.gv{font-size:18px;font-weight:bold;color:var(--am)}
.gl{font-size:10px;color:var(--mu);letter-spacing:1px;margin-top:4px}
.vt{background:#0d1825;border-radius:4px;height:8px;margin:4px 0;overflow:hidden}
.vf{height:100%;border-radius:4px;background:linear-gradient(90deg,#00ff88 0%,#ffaa00 50%,#ff4444 100%)}
.rec-box{border-radius:8px;padding:20px;border-width:2px;border-style:solid}
::-webkit-scrollbar{width:4px}::-webkit-scrollbar-track{background:#0a1520}::-webkit-scrollbar-thumb{background:#1a3a55}
@media(max-width:1100px){.g6{grid-template-columns:1fr 1fr 1fr}}
@media(max-width:800px){.g2,.g3,.g4,.g6{grid-template-columns:1fr 1fr}}
@media(max-width:480px){.g2,.g3,.g4,.g6{grid-template-columns:1fr}}
"""


def _index_bar_html(nifty, niftybank, sensex, vix, usdinr):
    """Render the top horizontal index bar."""
    items = [
        ("NIFTY 50",   f"₹{nifty['price']:,.2f}",  nifty.get('day_pct',0)),
        ("BANK NIFTY", f"₹{niftybank['price']:,.0f}", niftybank.get('day_pct',0)),
        ("SENSEX",     f"₹{sensex['price']:,.2f}",  sensex.get('pct',0)),
        ("USD/INR",    f"₹{usdinr:.2f}",             0),
        ("INDIA VIX",  f"{vix:.2f}%",                0),
    ]
    html = '<div class="index-bar">'
    for name, val, pct in items:
        c = "#00ff88" if pct > 0 else "#ff4444" if pct < 0 else "#00cfff"
        sign = "▲" if pct > 0 else "▼" if pct < 0 else "—"
        html += f'''<div class="ib">
          <span class="ib-name">{name}</span>
          <span class="ib-val" style="color:{c}">{val}</span>
          <span class="ib-chg" style="color:{c}">{sign} {abs(pct):.2f}%</span>
        </div>'''
    html += '</div>'
    return html


def _nav_bar(active="p1"):
    return f'''<div class="nav">
      <a href="http://127.0.0.1:8765/nifty_dashboard_live.html" class="{"active" if active=="p1" else ""}">⬡ NIFTY MC TERMINAL</a>
      <a href="http://127.0.0.1:8765/nifty_intelligence.html" class="{"active" if active=="p2" else ""}">🧠 STOCK INTELLIGENCE</a>
    </div>'''


# ─────────────────────────────────────────────────────────────
#  PAGE 1 HTML BUILDER  (original dashboard, enhanced)
# ─────────────────────────────────────────────────────────────
def build_page1_html(mkt, sim, fetch_time):
    n     = mkt["nifty"]
    price = n["price"]
    vix   = mkt["vix"]
    up    = n["day_pct"] >= 0
    days  = list(range(HORIZON + 1))
    nb    = mkt["niftybank"]
    nb_up = nb["day_pct"] >= 0
    sx    = mkt.get("sensex", {"price":0,"pct":0})

    # Stock rows
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

    # Probability rows
    prob_rows_html = ""
    for name, target, pct_val, side in sim["probs"]:
        c2  = "#00ff88" if side == "bull" else "#ff4444"
        bg  = "rgba(0,255,136,0.04)" if side == "bull" else "rgba(255,68,68,0.04)"
        tgt = f"₹{target:,}" if target else "—"
        bw  = min(pct_val, 100)
        prob_rows_html += f"""<tr style="background:{bg}">
  <td style="color:#ccc">{name}</td>
  <td style="text-align:center;color:#aaa">{tgt}</td>
  <td style="text-align:center;font-weight:bold;font-size:14px;color:{c2}">{pct_val}%</td>
  <td><div style="background:#0d1825;border-radius:3px;height:9px;overflow:hidden">
    <div style="width:{bw}%;height:100%;background:{c2};border-radius:3px"></div>
  </div></td>
</tr>"""

    # Percentile rows
    perc_rows_html = ""
    for pk, pv in [("P1",sim["p1"]),("P5",sim["p5"]),("P10",sim["p10"]),
                   ("P25",sim["p25"]),("Median",sim["median"]),
                   ("Mean",sim["expected"]),("P75",sim["p75"]),
                   ("P90",sim["p90"]),("P95",sim["p95"]),("P99",sim["p99"])]:
        chg  = round((pv/price-1)*100, 2)
        c2   = "#00ff88" if chg >= 0 else "#ff4444"
        bold = "font-weight:bold;" if pk in ("Mean","Median") else ""
        perc_rows_html += f"""<tr>
  <td style="color:#aaa;{bold}">{pk}</td>
  <td style="color:#eee;{bold}">₹{pv:,.1f}</td>
  <td style="color:{c2};font-weight:bold">{'+' if chg>=0 else ''}{chg}%</td>
</tr>"""

    # VIX
    vix_lbl  = ("LOW — options cheap" if vix < 15 else "MODERATE — fair pricing" if vix < 22 else "HIGH — elevated fear")
    vix_col  = "#00ff88" if vix < 15 else "#ffaa00" if vix < 22 else "#ff4444"
    vix_bar  = min(vix / 35 * 100, 100)

    # Tape
    tape_items = [
        ("NIFTY 50",     f"₹{price:,.2f}",                              "neu"),
        ("CHANGE",       f"{n['day_pct']:+.2f}%  ({n['day_change']:+.2f})", "up" if up else "dn"),
        ("OPEN",         f"₹{n['open']:,.2f}",                          "neu"),
        ("HIGH",         f"₹{n['high']:,.2f}",                          "up"),
        ("LOW",          f"₹{n['low']:,.2f}",                           "dn"),
        ("VOLUME",       fmt_vol(n['volume']),                          "neu"),
        ("52W HIGH",     f"₹{n['wk52_high']:,.2f}",                     "up"),
        ("52W LOW",      f"₹{n['wk52_low']:,.2f}",                      "dn"),
        ("INDIA VIX",    f"{vix:.2f}%",                                 "dn" if vix > 20 else "up"),
        ("BANK NIFTY",   f"₹{nb['price']:,.2f}  ({nb['day_pct']:+.2f}%)", "up" if nb_up else "dn"),
        ("USD/INR",      f"₹{mkt['usdinr']:.2f}",                      "neu"),
        ("SENSEX",       f"₹{sx['price']:,.2f}",                        "neu"),
        ("MC CALL",      f"₹{sim['mc_call']:,.2f}",                     "up"),
        ("MC PUT",       f"₹{sim['mc_put']:,.2f}",                      "dn"),
        ("EXPECTED D30", f"₹{sim['expected']:,.0f}",                    "neu"),
        ("SIGNAL",       sim['recommendation'].replace("⚡","").replace("📈","").replace("🛡","").replace("🔄","").strip(), "up"),
    ]
    tape_html = "".join(
        f'<span class="ti"><span class="tl">{l} </span><span class="tv {c3}">{v}</span></span>'
        for l, v, c3 in tape_items
    ) * 2

    # JSON data for charts
    j_candle_dates = json.dumps([d["date"]   for d in n["candles"]])
    j_candle_open  = json.dumps([d["open"]   for d in n["candles"]])
    j_candle_high  = json.dumps([d["high"]   for d in n["candles"]])
    j_candle_low   = json.dumps([d["low"]    for d in n["candles"]])
    j_candle_close = json.dumps([d["close"]  for d in n["candles"]])
    j_candle_vol   = json.dumps([d["volume"] for d in n["candles"]])
    j_vix          = json.dumps(mkt["vix_series"])
    j_paths        = json.dumps(sim["sample_paths"])
    j_days         = json.dumps(days)
    j_hist_x       = json.dumps(sim["hist_x"])
    j_hist_y       = json.dumps(sim["hist_y"])

    index_bar = _index_bar_html(n, nb, sx, vix, mkt["usdinr"])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="{REFRESH_SECONDS}">
<title>NIFTY 50 MC Terminal — {fetch_time}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
{SHARED_CSS}
.hero{{display:flex;align-items:flex-end;gap:20px;padding:14px 20px 8px;flex-wrap:wrap}}
.pm{{font-size:52px;font-weight:bold;font-family:'Courier New',monospace}}
.pc{{font-size:20px;font-weight:bold;margin-bottom:10px}}
.meta{{color:var(--mu);font-size:12px;line-height:2}}
</style>
</head>
<body>
<div class="hdr">
  <div>
    <div class="logo">⬡ NIFTY 50 LIVE MONTE CARLO TERMINAL</div>
    <div style="color:var(--mu);font-size:11px;margin-top:2px">
      yfinance data · Last fetched: <b style="color:var(--cy)">{fetch_time}</b>
      &nbsp;·&nbsp; Auto-refresh every <b style="color:var(--am)">{REFRESH_SECONDS}s</b>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:12px">
    {_nav_bar("p1")}
    <div style="text-align:right">
      <span class="badge-live">● LIVE</span>
      <div style="color:var(--am);font-size:11px;margin-top:3px">Next: <span id="cd">{REFRESH_SECONDS}</span>s</div>
    </div>
  </div>
</div>

{index_bar}
<div class="tape"><div class="tape-inner">{tape_html}</div></div>

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
      Realised Vol: {n['realised_vol']:.2f}%
    </div>
  </div>
  <div style="margin-left:auto;text-align:right">
    <div style="font-size:14px;font-weight:bold;padding:8px 16px;border-radius:5px;
      background:{'rgba(0,255,136,0.1)' if up else 'rgba(255,68,68,0.1)'};
      border:1px solid {'var(--gr)' if up else 'var(--rd)'};
      color:{'var(--gr)' if up else 'var(--rd)'}">
      {'▲ BULLISH' if up else '▼ BEARISH'}
    </div>
  </div>
</div>

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
      <div class="mv" style="font-size:13px">₹{sim['p5']:,.0f}–{sim['p95']:,.0f}</div>
      <div class="ms">90% confidence range</div>
    </div>
  </div>
</div>

<div class="g2" style="margin:0 16px;gap:12px">
  <div class="sec" style="margin:0">
    <h2>▸ 30-DAY OHLCV CANDLESTICK CHART</h2>
    <div id="ch-candle" style="height:340px"></div>
  </div>
  <div class="sec" style="margin:0">
    <h2>▸ INTRADAY INDIA VIX <span style="color:var(--mu);font-size:10px">1-min intervals</span></h2>
    <div id="ch-vix" style="height:340px"></div>
  </div>
</div>

<div class="g2" style="margin:8px 16px 0;gap:12px">
  <div class="sec" style="margin:0">
    <h2>▸ MONTE CARLO PATHS <span style="color:var(--mu);font-size:10px">200 of {N_PATHS:,} · 30 days</span></h2>
    <div id="ch-paths" style="height:330px"></div>
  </div>
  <div class="sec" style="margin:0">
    <h2>▸ CONFIDENCE BANDS <span style="color:var(--mu);font-size:10px">P5 · P25 · Mean · P75 · P95</span></h2>
    <div id="ch-bands" style="height:330px"></div>
  </div>
</div>

<div class="sec">
  <h2>▸ RETURN DISTRIBUTION AT DAY 30</h2>
  <div id="ch-hist" style="height:280px"></div>
</div>

<div class="sec">
  <h2>▸ TOP 10 NIFTY CONSTITUENTS</h2>
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

<div class="g2" style="margin:0 16px;gap:12px">
  <div class="sec" style="margin:0">
    <h2>▸ PERCENTILE TABLE <span style="color:var(--mu);font-size:10px">Day 30 from {N_PATHS:,} paths</span></h2>
    <table>
      <thead><tr><th>Percentile</th><th>Price (₹)</th><th>vs Today</th></tr></thead>
      <tbody>{perc_rows_html}</tbody>
    </table>
  </div>
  <div class="sec" style="margin:0">
    <h2>▸ OPTIONS PRICING <span style="color:var(--mu);font-size:10px">Strike ₹{STRIKE:,} · {T_DAYS}d · Vol {sim['blend_vol']:.2f}%</span></h2>
    <div class="g2" style="margin-bottom:14px">
      <div class="mc"><div class="ml">MC Call</div><div class="mv up">₹{sim['mc_call']:,.2f}</div><div class="ms">100k paths</div></div>
      <div class="mc"><div class="ml">BS Call</div><div class="mv neu">₹{sim['bs_call']:,.2f}</div><div class="ms">Analytical</div></div>
      <div class="mc"><div class="ml">MC Put</div><div class="mv dn">₹{sim['mc_put']:,.2f}</div><div class="ms">100k paths</div></div>
      <div class="mc"><div class="ml">BS Put</div><div class="mv amb">₹{sim['bs_put']:,.2f}</div><div class="ms">Analytical</div></div>
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
      Moneyness: {'OTM' if price < STRIKE else 'ITM'} ({((price/STRIKE-1)*100):+.1f}%)
    </div>
  </div>
</div>

<div class="sec">
  <h2>▸ TRADING RECOMMENDATION</h2>
  <div class="rec-box" style="border-color:{sim['rec_color']};background:rgba(0,0,0,0.25)">
    <div style="font-size:24px;font-weight:bold;letter-spacing:3px;color:{sim['rec_color']}">{sim['recommendation']}</div>
    <div style="margin-top:10px;color:#bbb;line-height:1.7;font-size:13px">{sim['rec_detail']}</div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:14px">
      <div style="padding:10px;background:var(--bg2);border-radius:6px;border:1px solid var(--bd)">
        <div style="color:var(--mu);font-size:10px;letter-spacing:1px">STRIKE / EXPIRY</div>
        <div style="color:var(--cy);font-size:16px;font-weight:bold;margin-top:4px">₹{STRIKE:,}  ·  {T_DAYS}d</div>
      </div>
      <div style="padding:10px;background:var(--bg2);border-radius:6px;border:1px solid var(--bd)">
        <div style="color:var(--mu);font-size:10px;letter-spacing:1px">DAILY 1-SIGMA MOVE</div>
        <div style="color:var(--am);font-size:16px;font-weight:bold;margin-top:4px">±₹{round(sim['sigma_daily']/100*price):,}  ({sim['sigma_daily']:.3f}%)</div>
      </div>
      <div style="padding:10px;background:var(--bg2);border-radius:6px;border:1px solid var(--bd)">
        <div style="color:var(--mu);font-size:10px;letter-spacing:1px">NEXT REFRESH</div>
        <div style="color:var(--am);font-size:16px;font-weight:bold;margin-top:4px"><span id="cd2">{REFRESH_SECONDS}</span>s</div>
      </div>
    </div>
    <div style="margin-top:12px;padding:10px;background:#050A0F;border-left:3px solid var(--am);color:#aaa;font-size:11px;line-height:1.8">
      <b style="color:var(--am)">⚠ RISK WARNING:</b> GBM model assumes log-normal returns and constant volatility.
      NOT investment advice. Always use stop-losses.
    </div>
  </div>
</div>

<div style="text-align:center;color:#334;padding:14px;font-size:11px;border-top:1px solid var(--bd);margin-top:8px">
  NIFTY 50 Live MC Terminal &nbsp;·&nbsp; Python + yfinance + Plotly &nbsp;·&nbsp;
  Fetched: {fetch_time} &nbsp;·&nbsp;
  <span style="color:var(--rd)">NOT INVESTMENT ADVICE</span>
</div>

<script>
let _s={REFRESH_SECONDS};
setInterval(()=>{{
  _s=Math.max(0,_s-1);
  ['cd','cd2'].forEach(id=>{{const e=document.getElementById(id);if(e)e.textContent=_s+'s';}});
}},1000);

const BG='#050A0F',G='#0d1e30',F='#99aabb';
const L={{paper_bgcolor:BG,plot_bgcolor:BG,font:{{color:F,family:'Courier New',size:11}},
  margin:{{t:20,b:45,l:65,r:20}},
  xaxis:{{gridcolor:G,zerolinecolor:G,color:F}},
  yaxis:{{gridcolor:G,zerolinecolor:G,color:F,tickformat:',.0f'}}}};
const CFG={{responsive:true,displayModeBar:false}};
const spot={price};

(()=>{{
  const dates={j_candle_dates},o={j_candle_open},h={j_candle_high},
        lo={j_candle_low},c={j_candle_close},v={j_candle_vol};
  if(!dates.length)return;
  Plotly.newPlot('ch-candle',[
    {{type:'candlestick',x:dates,open:o,high:h,low:lo,close:c,name:'NIFTY 50',
      increasing:{{line:{{color:'#00ff88'}},fillcolor:'rgba(0,255,136,0.45)'}},
      decreasing:{{line:{{color:'#ff4444'}},fillcolor:'rgba(255,68,68,0.45)'}},yaxis:'y'}},
    {{type:'bar',x:dates,y:v,name:'Volume',showlegend:false,
      marker:{{color:c.map((cl,i)=>cl>=o[i]?'rgba(0,255,136,0.28)':'rgba(255,68,68,0.28)')}},yaxis:'y2'}}
  ],Object.assign({{}},L,{{height:330,
    yaxis:Object.assign({{}},L.yaxis,{{title:'Price (₹)',domain:[0.28,1]}}),
    yaxis2:{{gridcolor:G,zerolinecolor:G,color:F,domain:[0,0.23],showticklabels:false}},
    xaxis:Object.assign({{}},L.xaxis,{{rangeslider:{{visible:false}}}}),
    legend:{{bgcolor:'rgba(0,0,0,0)',font:{{size:10}}}}
  }}),CFG);
}})();

(()=>{{
  const vd={j_vix};
  if(!vd.length)return;
  const xs=vd.map((_,i)=>i),last=vd[vd.length-1];
  const cl2=last>20?'#ff4444':last>15?'#ffaa00':'#00ff88';
  const fc=cl2.replace('#','').match(/../g).map(x=>parseInt(x,16));
  Plotly.newPlot('ch-vix',[
    {{x:xs,y:vd,mode:'lines',fill:'tozeroy',line:{{color:cl2,width:2}},
      fillcolor:`rgba(${{fc[0]}},${{fc[1]}},${{fc[2]}},0.1)`,name:'India VIX'}},
    {{x:[0,xs[xs.length-1]],y:[20,20],mode:'lines',line:{{color:'#ff4444',width:1,dash:'dot'}},name:'Fear (20)'}},
    {{x:[0,xs[xs.length-1]],y:[15,15],mode:'lines',line:{{color:'#ffaa00',width:1,dash:'dot'}},name:'Caution (15)'}}
  ],Object.assign({{}},L,{{height:330,
    xaxis:Object.assign({{}},L.xaxis,{{title:'Minutes'}}),
    yaxis:Object.assign({{}},L.yaxis,{{title:'VIX Level'}}),
    legend:{{bgcolor:'rgba(0,0,0,0)',font:{{size:10}}}}
  }}),CFG);
}})();

(()=>{{
  const paths={j_paths},days={j_days};
  if(!paths.length)return;
  const traces=[];
  for(let i=0;i<Math.min(paths.length,150);i++)
    traces.push({{x:days,y:paths[i],mode:'lines',line:{{color:'rgba(0,180,255,0.05)',width:1}},showlegend:false,hoverinfo:'skip'}});
  traces.push({{x:days,y:Array(days.length).fill(spot),mode:'lines',line:{{color:'rgba(255,255,255,0.35)',width:1.5,dash:'dot'}},name:'Spot'}});
  Plotly.newPlot('ch-paths',traces,Object.assign({{}},L,{{height:320,
    xaxis:Object.assign({{}},L.xaxis,{{title:'Trading Day'}}),
    yaxis:Object.assign({{}},L.yaxis,{{title:'Price (₹)'}}),
    legend:{{bgcolor:'rgba(0,0,0,0)',font:{{size:10}}}}
  }}),CFG);
}})();

(()=>{{
  const days={j_days},mu={sim['mu_daily']}/100,sigma={sim['sigma_daily']}/100;
  const t={{p5:{sim['p5']},p25:{sim['p25']},mn:{sim['expected']},p75:{sim['p75']},p95:{sim['p95']}}};
  function band(t30,darr){{return darr.map(d=>d===0?spot:spot*Math.exp((mu-0.5*sigma*sigma)*d+Math.log(t30/spot)*Math.sqrt(d/30)));}}
  const p5c=band(t.p5,days),p25c=band(t.p25,days),mnc=band(t.mn,days),p75c=band(t.p75,days),p95c=band(t.p95,days);
  Plotly.newPlot('ch-bands',[
    {{x:[...days,...[...days].reverse()],y:[...p95c,...p5c.slice().reverse()],fill:'toself',fillcolor:'rgba(0,180,255,0.07)',line:{{color:'transparent'}},name:'P5–P95'}},
    {{x:[...days,...[...days].reverse()],y:[...p75c,...p25c.slice().reverse()],fill:'toself',fillcolor:'rgba(0,180,255,0.14)',line:{{color:'transparent'}},name:'P25–P75'}},
    {{x:days,y:p5c,mode:'lines',line:{{color:'#ff4444',width:1.5,dash:'dash'}},name:'P5'}},
    {{x:days,y:p95c,mode:'lines',line:{{color:'#00ff88',width:1.5,dash:'dash'}},name:'P95'}},
    {{x:days,y:mnc,mode:'lines',line:{{color:'#00cfff',width:3}},name:'Mean'}},
    {{x:days,y:Array(days.length).fill(spot),mode:'lines',line:{{color:'rgba(255,255,255,0.3)',width:1,dash:'dot'}},showlegend:false}}
  ],Object.assign({{}},L,{{height:320,
    xaxis:Object.assign({{}},L.xaxis,{{title:'Trading Day'}}),
    yaxis:Object.assign({{}},L.yaxis,{{title:'Price (₹)'}}),
    legend:{{bgcolor:'rgba(0,0,0,0)',font:{{size:10}}}}
  }}),CFG);
}})();

(()=>{{
  const hx={j_hist_x},hy={j_hist_y};
  Plotly.newPlot('ch-hist',[{{
    x:hx,y:hy,type:'bar',
    marker:{{color:hx.map(v=>v>=spot?'rgba(0,255,136,0.7)':'rgba(255,68,68,0.7)')}},
    name:'Distribution'
  }}],Object.assign({{}},L,{{height:270,
    xaxis:Object.assign({{}},L.xaxis,{{title:'NIFTY 50 Price at Day 30 (₹)'}}),
    yaxis:Object.assign({{}},L.yaxis,{{title:'Frequency'}}),
    shapes:[{{type:'line',x0:spot,x1:spot,y0:0,y1:1,yref:'paper',line:{{color:'white',width:2,dash:'dot'}}}}],
    annotations:[{{x:spot,y:1,yref:'paper',text:'Spot ₹'+spot.toLocaleString(),showarrow:false,font:{{color:'white',size:11}},bgcolor:'#0d1825',yanchor:'bottom'}}]
  }}),CFG);
}})();
</script>
</body></html>"""
    return html


# ─────────────────────────────────────────────────────────────
#  PAGE 2 HTML BUILDER — Stock Intelligence
# ─────────────────────────────────────────────────────────────
def _pick_card(rec, rank, horizon_label):
    """Render a single pick card."""
    sig_col = rec["sig_col"]
    signal  = rec["signal"]
    ts = rec.get("tech_score", 50)
    fs = rec.get("fund_score", 50)
    ss = rec.get("sent_score", 50)
    comp = rec.get("composite", 50)
    sl_pct = round((rec["stop_loss"]/rec["price"]-1)*100, 1) if rec["price"] else 0
    t2_pct = round((rec["target2"]/rec["price"]-1)*100, 1) if rec["price"] else 0

    return f"""
<div class="card-pick" style="border-color:{sig_col}22">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">
    <div>
      <span style="color:{sig_col};font-size:16px;font-weight:bold">#{rank} {rec['ticker']}</span>
      <span style="color:#aaa;font-size:11px;margin-left:8px">{rec['name']}</span>
    </div>
    <span class="signal-badge" style="background:{sig_col}22;color:{sig_col};border:1px solid {sig_col}">{signal}</span>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px">
    <div>
      <div style="color:var(--mu);font-size:9px;letter-spacing:1px">PRICE</div>
      <div style="color:#eee;font-size:18px;font-weight:bold">₹{rec['price']:,.2f}</div>
    </div>
    <div>
      <div style="color:var(--mu);font-size:9px;letter-spacing:1px">COMPOSITE</div>
      <div style="color:{sig_col};font-size:18px;font-weight:bold">{comp}/100</div>
      <div class="score-bar"><div class="score-fill" style="width:{comp}%;background:{sig_col}"></div></div>
    </div>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;font-size:11px;margin-bottom:12px">
    <div style="background:var(--bg);border-radius:4px;padding:6px">
      <div style="color:var(--mu);font-size:9px">ENTRY</div>
      <div style="color:#eee;font-weight:bold">₹{rec['entry']:,.2f}</div>
    </div>
    <div style="background:var(--bg);border-radius:4px;padding:6px">
      <div style="color:var(--mu);font-size:9px">STOP LOSS</div>
      <div style="color:#ff4444;font-weight:bold">₹{rec['stop_loss']:,.2f} <span style="color:#667">({sl_pct:+.1f}%)</span></div>
    </div>
    <div style="background:var(--bg);border-radius:4px;padding:6px">
      <div style="color:var(--mu);font-size:9px">TARGET 2</div>
      <div style="color:#00ff88;font-weight:bold">₹{rec['target2']:,.2f} <span style="color:#667">({t2_pct:+.1f}%)</span></div>
    </div>
  </div>

  <div style="display:flex;gap:6px;margin-bottom:10px;font-size:10px">
    <div style="flex:1;background:rgba(0,207,255,0.08);border-radius:4px;padding:5px;text-align:center">
      <div style="color:var(--mu)">TECH</div>
      <div style="color:#00cfff;font-weight:bold">{ts}</div>
    </div>
    <div style="flex:1;background:rgba(204,136,255,0.08);border-radius:4px;padding:5px;text-align:center">
      <div style="color:var(--mu)">FUND</div>
      <div style="color:#cc88ff;font-weight:bold">{fs}</div>
    </div>
    <div style="flex:1;background:rgba(255,170,0,0.08);border-radius:4px;padding:5px;text-align:center">
      <div style="color:var(--mu)">SENT</div>
      <div style="color:#ffaa00;font-weight:bold">{ss:.0f}</div>
    </div>
    <div style="flex:1;background:rgba(0,255,136,0.08);border-radius:4px;padding:5px;text-align:center">
      <div style="color:var(--mu)">R:R</div>
      <div style="color:#00ff88;font-weight:bold">1:{rec['rr_ratio']}</div>
    </div>
  </div>

  <div style="font-size:11px;color:#889;line-height:1.6;border-top:1px solid var(--bd);padding-top:8px">
    {rec['rationale'][:200]}...
  </div>

  <div style="margin-top:8px;display:flex;gap:6px;font-size:9px">
    <span style="background:rgba(0,255,136,0.1);color:#00ff88;border:1px solid #00ff8844;border-radius:3px;padding:2px 6px">T1: ₹{rec['target1']:,.0f}</span>
    <span style="background:rgba(0,255,136,0.1);color:#00ff88;border:1px solid #00ff8844;border-radius:3px;padding:2px 6px">T2: ₹{rec['target2']:,.0f}</span>
    <span style="background:rgba(0,255,136,0.1);color:#00ff88;border:1px solid #00ff8844;border-radius:3px;padding:2px 6px">T3: ₹{rec['target3']:,.0f}</span>
  </div>
</div>"""


def _screener_table_row(s, rank):
    sig_col = s["sig_col"]
    ts = s["tech_score"]; fs = s["fund_score"]; ss = s.get("sent_score",50)
    comp = s["composite"]

    def score_cell(v, color):
        return f'<td style="text-align:center"><div style="color:{color};font-weight:bold">{v}</div><div class="score-bar"><div class="score-fill" style="width:{v}%;background:{color}"></div></div></td>'

    pct_c = "#00ff88" if s["pct"] >= 0 else "#ff4444"
    return f"""<tr>
  <td style="color:var(--mu)">{rank}</td>
  <td style="color:var(--cy);font-weight:bold">{s['ticker']}</td>
  <td style="color:#ccc">{s['name']}</td>
  <td style="text-align:right;color:#eee">₹{s['price']:,.2f}</td>
  <td style="text-align:right;color:{pct_c};font-weight:bold">{s['pct']:+.2f}%</td>
  {score_cell(ts,'#00cfff')}
  {score_cell(fs,'#cc88ff')}
  {score_cell(int(ss),'#ffaa00')}
  <td style="text-align:center;font-size:15px;font-weight:bold;color:{sig_col}">{comp}</td>
  <td style="text-align:center">
    <span class="signal-badge" style="background:{sig_col}22;color:{sig_col};border:1px solid {sig_col}">{s['signal']}</span>
  </td>
  <td style="color:#888;font-size:11px">{s.get('sector','')[:20]}</td>
</tr>"""


def _news_rows(articles):
    if not articles:
        return '<tr><td colspan="3" style="text-align:center;color:#445;padding:20px">No news fetched</td></tr>'
    rows = ""
    for a in articles[:8]:
        lbl = a.get("label","neutral")
        c2 = "#00ff88" if lbl=="positive" else "#ff4444" if lbl=="negative" else "#ffaa00"
        rows += f"""<tr>
  <td style="color:#bbb;font-size:11px">{a['title'][:100]}</td>
  <td style="color:#667;font-size:10px">{a.get('source','')}</td>
  <td style="text-align:center">
    <span style="color:{c2};font-size:10px;font-weight:bold">{lbl.upper()} ({a['score']:.0f})</span>
  </td>
</tr>"""
    return rows


def build_page2_html(mkt, screener_data, top_intraday, top_longterm,
                     market_sentiment, fetch_time):
    """Build the full Stock Intelligence page HTML."""
    n   = mkt["nifty"]
    nb  = mkt["niftybank"]
    sx  = mkt.get("sensex", {"price":0,"pct":0})
    vix = mkt["vix"]

    index_bar = _index_bar_html(n, nb, sx, vix, mkt["usdinr"])

    # Build screener table
    screener_rows = ""
    for i, s in enumerate(screener_data[:20], 1):
        screener_rows += _screener_table_row(s, i)

    # Build intraday cards
    intraday_cards = ""
    for i, rec in enumerate(top_intraday, 1):
        intraday_cards += _pick_card(rec["intraday"], i, "Intraday")

    # Build long-term cards
    longterm_cards = ""
    for i, rec in enumerate(top_longterm, 1):
        longterm_cards += _pick_card(rec["longterm"], i, "Long-Term")

    # Market sentiment section
    ms = market_sentiment
    ms_lbl, ms_col = sentiment_label_display(ms.get("score", 50))
    ms_bar = ms.get("score", 50)

    # News rows
    news_html = _news_rows(ms.get("articles", []))

    # Radar chart data for top 5 stocks
    radar_labels = json.dumps(["Tech", "Fundamental", "Sentiment", "Momentum", "Value"])
    radar_stocks = []
    for s in screener_data[:5]:
        mom = min(100, max(0, 50 + s.get("indicators",{}).get("momentum",{}).get("roc",0) * 5))
        pe = s.get("pe")
        val = 70 if (pe and 10 < pe < 25) else 50 if (pe and pe < 35) else 30
        radar_stocks.append({
            "name":  s["ticker"],
            "scores": [s["tech_score"], s["fund_score"], s.get("sent_score",50), round(mom,1), val]
        })
    j_radar = json.dumps(radar_stocks)

    # Score distribution bar chart
    all_composites = json.dumps([s["composite"] for s in screener_data])
    all_tickers    = json.dumps([s["ticker"] for s in screener_data])
    all_colors     = json.dumps([s["sig_col"] for s in screener_data])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="{REFRESH_SECONDS}">
<title>Stock Intelligence — {fetch_time}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
{SHARED_CSS}
.search-box{{background:var(--bg2);border:1px solid var(--bd);border-radius:6px;padding:16px;margin:8px 16px}}
.search-input{{background:var(--bg);border:1px solid var(--bd);color:var(--tx);padding:10px 16px;
  border-radius:4px;font-family:var(--font);font-size:13px;width:100%;letter-spacing:1px;outline:none}}
.search-input:focus{{border-color:var(--cy)}}
.search-btn{{background:var(--cy);color:#050A0F;border:none;padding:10px 22px;border-radius:4px;
  cursor:pointer;font-family:var(--font);font-size:13px;font-weight:bold;letter-spacing:1px;margin-left:8px}}
.search-btn:hover{{background:#00e6ff}}
#search-result{{display:none;margin-top:14px}}
.ai-box{{background:var(--bg);border:1px solid #1a4060;border-radius:6px;padding:14px;
  font-size:13px;color:#bbb;line-height:1.8;min-height:60px}}
.ai-thinking{{color:var(--am);font-style:italic}}
.peer-table th{{font-size:9px}}
.peer-table td{{font-size:11px}}
.picks-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:12px;margin-top:12px}}
</style>
</head>
<body>
<div class="hdr">
  <div>
    <div class="logo">🧠 STOCK INTELLIGENCE ENGINE</div>
    <div style="color:var(--mu);font-size:11px;margin-top:2px">
      15 Technical + 15 Fundamental + Sentiment · Fetched: <b style="color:var(--cy)">{fetch_time}</b>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:12px">
    {_nav_bar("p2")}
    <div style="text-align:right">
      <span class="badge-live">● LIVE</span>
      <div style="color:var(--am);font-size:11px;margin-top:3px">Next: <span id="cd">{REFRESH_SECONDS}</span>s</div>
    </div>
  </div>
</div>

{index_bar}

<!-- MARKET SENTIMENT BANNER -->
<div style="background:{'rgba(0,255,136,0.06)' if ms_lbl in ('BULLISH','MILDLY BULLISH') else 'rgba(255,68,68,0.06)'};
  border-bottom:1px solid var(--bd);padding:8px 20px;display:flex;align-items:center;gap:16px;flex-wrap:wrap">
  <div style="font-size:11px;color:var(--mu);letter-spacing:1px">MARKET SENTIMENT</div>
  <div style="font-size:14px;font-weight:bold;color:{ms_col}">{ms_lbl}</div>
  <div style="flex:1;max-width:200px;background:var(--bg2);border-radius:10px;height:6px;overflow:hidden">
    <div style="width:{ms_bar}%;height:100%;background:{ms_col};border-radius:10px"></div>
  </div>
  <div style="font-size:12px;color:#aaa">
    Score: <b style="color:{ms_col}">{ms.get('score',50):.0f}/100</b> &nbsp;·&nbsp;
    <span style="color:#00ff88">▲ {ms.get('positive_count',0)} positive</span> &nbsp;·&nbsp;
    <span style="color:#ff4444">▼ {ms.get('negative_count',0)} negative</span> &nbsp;·&nbsp;
    <span style="color:#ffaa00">— {ms.get('neutral_count',0)} neutral</span>
  </div>
</div>

<!-- SEARCH BAR -->
<div class="search-box">
  <h2 style="margin-bottom:12px">▸ STOCK SEARCH & ANALYSIS</h2>
  <div style="display:flex;align-items:center">
    <input id="search-ticker" class="search-input" type="text"
      placeholder="Search ticker (e.g. RELIANCE, TCS, INFY, HDFCBANK) — press Enter or click Analyse"
      style="flex:1" />
    <button class="search-btn" onclick="doSearch()">ANALYSE</button>
  </div>
  <div id="search-result">
    <div id="ai-response" class="ai-box" style="margin-top:12px"></div>
    <div class="g2" style="margin-top:12px;gap:10px">
      <div id="search-tech-table" style="overflow-x:auto"></div>
      <div id="search-fund-table" style="overflow-x:auto"></div>
    </div>
    <div style="margin-top:10px" id="search-charts">
      <div class="g2" style="gap:10px">
        <div class="sec" style="margin:0"><h2>▸ PRICE + MA CHART</h2><div id="ch-search-price" style="height:260px"></div></div>
        <div class="sec" style="margin:0"><h2>▸ RSI (14)</h2><div id="ch-search-rsi" style="height:260px"></div></div>
      </div>
    </div>
  </div>
</div>

<!-- TOP INTRADAY PICKS -->
<div class="sec">
  <h2>▸ TOP 5 INTRADAY PICKS
    <span style="color:var(--mu);font-size:10px;font-weight:normal;margin-left:8px">Ranked by Tech Score × Sentiment · Today's session</span>
  </h2>
  <div class="picks-grid">{intraday_cards}</div>
</div>

<!-- TOP LONG-TERM PICKS -->
<div class="sec">
  <h2>▸ TOP 5 LONG-TERM PICKS
    <span style="color:var(--mu);font-size:10px;font-weight:normal;margin-left:8px">Ranked by Fundamental + Technical + Sentiment composite</span>
  </h2>
  <div class="picks-grid">{longterm_cards}</div>
</div>

<!-- SCREENER TABLE -->
<div class="sec">
  <h2>▸ FULL SCREENER RANKINGS
    <span style="color:var(--mu);font-size:10px;font-weight:normal;margin-left:8px">All {len(screener_data)} screened stocks · Composite score</span>
  </h2>
  <div style="overflow-x:auto">
    <table>
      <thead><tr>
        <th>#</th><th>Ticker</th><th>Name</th>
        <th style="text-align:right">Price</th><th style="text-align:right">Day%</th>
        <th style="text-align:center">Tech (0-100)</th>
        <th style="text-align:center">Fund (0-100)</th>
        <th style="text-align:center">Sent (0-100)</th>
        <th style="text-align:center">Composite</th>
        <th style="text-align:center">Signal</th>
        <th>Sector</th>
      </tr></thead>
      <tbody>{screener_rows}</tbody>
    </table>
  </div>
</div>

<!-- SCORE CHARTS ROW -->
<div class="g2" style="margin:0 16px;gap:12px">
  <div class="sec" style="margin:0">
    <h2>▸ COMPOSITE SCORE DISTRIBUTION</h2>
    <div id="ch-scores" style="height:300px"></div>
  </div>
  <div class="sec" style="margin:0">
    <h2>▸ TOP 5 STOCKS RADAR</h2>
    <div id="ch-radar" style="height:300px"></div>
  </div>
</div>

<!-- PEER COMPARISON TOOL -->
<div class="sec">
  <h2>▸ PEER COMPARISON TOOL
    <span style="color:var(--mu);font-size:10px;font-weight:normal;margin-left:8px">Edit tickers below and click Compare</span>
  </h2>
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;flex-wrap:wrap">
    <input id="peer1" type="text" class="search-input" style="width:120px" value="RELIANCE"/>
    <input id="peer2" type="text" class="search-input" style="width:120px" value="TCS"/>
    <input id="peer3" type="text" class="search-input" style="width:120px" value="INFY"/>
    <input id="peer4" type="text" class="search-input" style="width:120px" value="WIPRO"/>
    <button class="search-btn" onclick="doPeerCompare()">COMPARE</button>
  </div>
  <div id="peer-result">
    <div style="color:#445;text-align:center;padding:20px;font-size:12px">Enter tickers and click Compare to see peer analysis</div>
  </div>
</div>

<!-- MARKET NEWS -->
<div class="sec">
  <h2>▸ MARKET NEWS SENTIMENT
    <span style="color:var(--mu);font-size:10px;font-weight:normal;margin-left:8px">{ms.get('article_count',0)} articles analysed</span>
  </h2>
  <table>
    <thead><tr><th>Headline</th><th>Source</th><th style="text-align:center">Sentiment</th></tr></thead>
    <tbody>{news_html}</tbody>
  </table>
</div>

<div style="text-align:center;color:#334;padding:14px;font-size:11px;border-top:1px solid var(--bd);margin-top:8px">
  Stock Intelligence Engine &nbsp;·&nbsp; Python + yfinance + NLP &nbsp;·&nbsp;
  Fetched: {fetch_time} &nbsp;·&nbsp;
  <span style="color:var(--rd)">NOT INVESTMENT ADVICE</span>
</div>

<script>
let _s={REFRESH_SECONDS};
setInterval(()=>{{_s=Math.max(0,_s-1);const e=document.getElementById('cd');if(e)e.textContent=_s+'s';}},1000);

const BG='#050A0F',G='#0d1e30',F='#99aabb';
const L={{paper_bgcolor:BG,plot_bgcolor:BG,font:{{color:F,family:'Courier New',size:11}},
  margin:{{t:20,b:40,l:55,r:20}},
  xaxis:{{gridcolor:G,zerolinecolor:G,color:F}},
  yaxis:{{gridcolor:G,zerolinecolor:G,color:F}}}};
const CFG={{responsive:true,displayModeBar:false}};

// Score distribution bar chart
(()=>{{
  const tickers={all_tickers}, scores={all_composites}, colors={all_colors};
  Plotly.newPlot('ch-scores',[{{
    x:tickers, y:scores, type:'bar',
    marker:{{color:scores.map(s=>s>=65?'rgba(0,255,136,0.7)':s<=38?'rgba(255,68,68,0.7)':'rgba(255,170,0,0.7)')}},
    text:scores.map(s=>s+''),textposition:'outside',
  }}],Object.assign({{}},L,{{
    height:290,
    xaxis:Object.assign({{}},L.xaxis,{{tickangle:-45}}),
    yaxis:Object.assign({{}},L.yaxis,{{title:'Composite Score',range:[0,110]}}),
    shapes:[
      {{type:'line',x0:-0.5,x1:tickers.length-0.5,y0:65,y1:65,line:{{color:'#00ff88',dash:'dot',width:1}}}},
      {{type:'line',x0:-0.5,x1:tickers.length-0.5,y0:38,y1:38,line:{{color:'#ff4444',dash:'dot',width:1}}}}
    ]
  }}),CFG);
}})();

// Radar chart
(()=>{{
  const radarStocks={j_radar};
  const labels={radar_labels};
  const traces=radarStocks.map(s=>{{
    const vals=[...s.scores,s.scores[0]];
    const lbls=[...labels,labels[0]];
    return {{
      type:'scatterpolar',r:vals,theta:lbls,fill:'toself',name:s.name,
      opacity:0.7,
      line:{{width:2}}
    }};
  }});
  Plotly.newPlot('ch-radar',traces,Object.assign({{}},L,{{
    height:290,
    polar:{{bgcolor:BG,radialaxis:{{visible:true,range:[0,100],color:F,gridcolor:G}},
           angularaxis:{{color:F,gridcolor:G}}}},
    paper_bgcolor:BG,
    legend:{{bgcolor:'rgba(0,0,0,0)',font:{{size:10}}}},
    margin:{{t:20,b:20,l:30,r:30}}
  }}),CFG);
}})();

// — SEARCH functionality —————————————————————————————————
document.getElementById('search-ticker').addEventListener('keydown', e => {{
  if(e.key==='Enter') doSearch();
}});

function doSearch(){{
  const ticker=(document.getElementById('search-ticker').value||'').trim().toUpperCase();
  if(!ticker) return;
  const result=document.getElementById('search-result');
  const ai=document.getElementById('ai-response');
  result.style.display='block';
  ai.innerHTML='<span class="ai-thinking">⟳ Analysing '+ticker+' with 15 technical + 15 fundamental indicators + AI insight...</span>';
  document.getElementById('search-tech-table').innerHTML='';
  document.getElementById('search-fund-table').innerHTML='';

  fetch('http://127.0.0.1:8765/search?ticker='+encodeURIComponent(ticker))
    .then(r=>r.json())
    .then(data=>{{
      if(data.error){{
        ai.innerHTML='<span style="color:#ff4444">'+data.error+'</span>';
        return;
      }}
      renderSearchResult(data);
    }})
    .catch(()=>{{
      // Standalone mode — show cached data if available
      const cached=getScreeerData(ticker);
      if(cached) renderSearchResult(cached);
      else ai.innerHTML='<span style="color:#ffaa00">Run with main.py server for live search. Showing screener cache if available.</span>';
    }});
}}

function getScreeerData(ticker){{
  // Look for the ticker in screener data embedded in the page
  return null;
}}

function renderSearchResult(data){{
  const ai=document.getElementById('ai-response');
  const sig_col=data.signal==='BUY'?'#00ff88':data.signal==='SELL'?'#ff4444':'#ffaa00';
  let html=`<b style="color:${{sig_col}};font-size:16px">${{data.signal}} — ${{data.name}}</b>
    <span style="color:#aaa;margin-left:10px">₹${{data.price?.toLocaleString()}} · Composite: ${{data.composite}}/100</span>
    <br><br>${{data.rationale||''}}
    <br><br><b style="color:var(--cy)">Entry:</b> ₹${{data.entry}} &nbsp;
    <b style="color:#ff4444">Stop:</b> ₹${{data.sl}} &nbsp;
    <b style="color:#00ff88">T1:</b> ₹${{data.t1}} &nbsp;
    <b style="color:#00ff88">T2:</b> ₹${{data.t2}} &nbsp;
    <b style="color:#00ff88">T3:</b> ₹${{data.t3}}`;
  ai.innerHTML=html;

  // Technical table
  if(data.tech_rows){{
    let tbl='<table class="peer-table"><thead><tr><th>Indicator</th><th>Value</th><th>Signal</th></tr></thead><tbody>';
    data.tech_rows.forEach(r=>{{
      tbl+=`<tr><td style="color:#aaa">${{r[0]}}</td><td style="color:#eee">${{r[1]}}</td>
              <td><span style="color:${{r[3]}};font-size:10px">${{r[2]}}</span></td></tr>`;
    }});
    tbl+='</tbody></table>';
    document.getElementById('search-tech-table').innerHTML='<div class="sec" style="margin:0"><h2>▸ 15 TECHNICAL INDICATORS</h2>'+tbl+'</div>';
  }}

  // Fundamental table
  if(data.fund_rows){{
    let tbl='<table class="peer-table"><thead><tr><th>Metric</th><th>Value</th><th>Assessment</th></tr></thead><tbody>';
    data.fund_rows.forEach(r=>{{
      tbl+=`<tr><td style="color:#aaa">${{r[0]}}</td><td style="color:#eee">${{r[1]}}</td>
              <td><span style="color:${{r[3]}};font-size:10px">${{r[2]}}</span></td></tr>`;
    }});
    tbl+='</tbody></table>';
    document.getElementById('search-fund-table').innerHTML='<div class="sec" style="margin:0"><h2>▸ 15 FUNDAMENTAL METRICS</h2>'+tbl+'</div>';
  }}

  // Charts
  if(data.closes && data.closes.length){{
    const xs=data.closes.map((_,i)=>i);
    const traces=[
      {{x:xs,y:data.closes,mode:'lines',name:'Close',line:{{color:'#00cfff',width:2}}}},
    ];
    if(data.ma20) traces.push({{x:xs,y:data.ma20,mode:'lines',name:'MA20',line:{{color:'#00ff88',width:1,dash:'dot'}}}});
    if(data.ma50) traces.push({{x:xs,y:data.ma50,mode:'lines',name:'MA50',line:{{color:'#ffaa00',width:1,dash:'dot'}}}});
    Plotly.newPlot('ch-search-price',traces,Object.assign({{}},L,{{height:250,
      yaxis:Object.assign({{}},L.yaxis,{{title:'Price (₹)'}})
    }}),CFG);
  }}
  if(data.rsi_series && data.rsi_series.length){{
    const xs=data.rsi_series.map((_,i)=>i);
    Plotly.newPlot('ch-search-rsi',[
      {{x:xs,y:data.rsi_series,mode:'lines',name:'RSI',line:{{color:'#cc88ff',width:2}}}},
      {{x:[0,xs[xs.length-1]],y:[70,70],mode:'lines',line:{{color:'#ff4444',dash:'dot',width:1}},name:'OB (70)'}},
      {{x:[0,xs[xs.length-1]],y:[30,30],mode:'lines',line:{{color:'#00ff88',dash:'dot',width:1}},name:'OS (30)'}}
    ],Object.assign({{}},L,{{height:250,
      yaxis:Object.assign({{}},L.yaxis,{{title:'RSI',range:[0,100]}})
    }}),CFG);
  }}
}}

// — PEER COMPARISON ——————————————————————————————————————
function doPeerCompare(){{
  const tickers=['peer1','peer2','peer3','peer4'].map(id=>document.getElementById(id).value.trim().toUpperCase()).filter(Boolean);
  const res=document.getElementById('peer-result');
  res.innerHTML='<div style="color:var(--am);padding:20px;text-align:center">⟳ Fetching peer data...</div>';

  const params=tickers.map(t=>'t='+encodeURIComponent(t)).join('&');
  fetch('http://127.0.0.1:8765/peer?'+params)
    .then(r=>r.json())
    .then(data=>renderPeerTable(data))
    .catch(()=>{{
      res.innerHTML='<div style="color:#ffaa00;padding:20px">Run with main.py server for live peer comparison.</div>';
    }});
}}

function renderPeerTable(peers){{
  if(!peers||!peers.length)return;
  const res=document.getElementById('peer-result');
  const metrics=['P/E','P/B','ROE%','ROCE%','EPS Growth','Rev Growth','D/E','Current Ratio','Op Margin','Net Margin'];
  let tbl='<div style="overflow-x:auto"><table class="peer-table"><thead><tr><th>Metric</th>';
  peers.forEach(p=>{{tbl+=`<th style="text-align:right">${{p.ticker}}</th>`;}}); tbl+='</tr></thead><tbody>';

  const fundKeys=['pe','pb','roe','roce','eps_growth','revenue_growth','debt_equity','current_ratio','operating_margin','net_margin'];
  fundKeys.forEach((k,i)=>{{
    const vals=peers.map(p=>p.fund?.[k]);
    const numVals=vals.filter(v=>v!=null&&!isNaN(v));
    if(!numVals.length) return;
    const best=Math.max(...numVals), worst=Math.min(...numVals);
    tbl+=`<tr><td style="color:#aaa">${{metrics[i]}}</td>`;
    vals.forEach(v=>{{
      if(v==null){{tbl+='<td style="text-align:right;color:#445">N/A</td>';return;}}
      const c2=Math.abs(v-best)<0.01?'#00ff88':Math.abs(v-worst)<0.01?'#ff4444':'#eee';
      tbl+=`<td style="text-align:right;color:${{c2}};font-weight:${{c2!='#eee'?'bold':'normal'}}">${{typeof v==='number'?v.toFixed(1):'—'}}</td>`;
    }});
    tbl+='</tr>';
  }});

  // Composite scores row
  tbl+='<tr style="border-top:2px solid var(--bd)"><td style="color:var(--cy);font-weight:bold">Composite Score</td>';
  peers.forEach(p=>{{
    const c2=p.composite>=65?'#00ff88':p.composite<=38?'#ff4444':'#ffaa00';
    tbl+=`<td style="text-align:right;color:${{c2}};font-weight:bold">${{p.composite}}</td>`;
  }});
  tbl+='</tr></tbody></table></div>';
  res.innerHTML=tbl;

  // Peer bar chart
  const chartDiv=document.createElement('div');
  chartDiv.id='ch-peer';chartDiv.style.height='240px';chartDiv.style.marginTop='12px';
  res.appendChild(chartDiv);

  Plotly.newPlot('ch-peer',[
    {{x:peers.map(p=>p.ticker),y:peers.map(p=>p.tech_score),type:'bar',name:'Tech',marker:{{color:'rgba(0,207,255,0.7)'}}}},
    {{x:peers.map(p=>p.ticker),y:peers.map(p=>p.fund_score),type:'bar',name:'Fund',marker:{{color:'rgba(204,136,255,0.7)'}}}},
    {{x:peers.map(p=>p.ticker),y:peers.map(p=>p.sent_score||50),type:'bar',name:'Sentiment',marker:{{color:'rgba(255,170,0,0.7)'}}}},
  ],Object.assign({{}},L,{{
    height:230,barmode:'group',
    yaxis:Object.assign({{}},L.yaxis,{{title:'Score (0-100)',range:[0,110]}}),
    legend:{{bgcolor:'rgba(0,0,0,0)'}}
  }}),CFG);
}}
</script>
</body></html>"""
    return html