import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.stats import norm
import yfinance as yf
import time

# ================= CONFIG =================
TICKER = "^NSEI"
FALLBACK_TICKER = "NIFTYBEES.NS"
VIX_TICKER = "^INDIAVIX"

SIMULATIONS = 10000
DAYS = 30
RISK_FREE = 0.065
REFRESH_SECONDS = 60

# ================= SAFE FETCH =================
def fetch_data(ticker, period="1y"):
    try:
        df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return None

# ================= SAFE VALUE =================
def get_last(series):
    if series is None or series.empty:
        return None
    series = series.dropna()
    if len(series) == 0:
        return None
    val = series.iloc[-1]
    if isinstance(val, pd.Series):
        val = val.values[0]
    return float(val)

# ================= BLACK-SCHOLES =================
def bs(S,K,T,r,sigma,opt="call"):
    d1=(np.log(S/K)+(r+0.5*sigma**2)*T)/(sigma*np.sqrt(T))
    d2=d1-sigma*np.sqrt(T)
    if opt=="call":
        return S*norm.cdf(d1)-K*np.exp(-r*T)*norm.cdf(d2)
    else:
        return K*np.exp(-r*T)*norm.cdf(-d2)-S*norm.cdf(-d1)

# ================= PROB =================
def prob(x):
    return float(round(np.mean(x)*100,2))

# ================= MAIN =================
def run_dashboard():

    # ===== FETCH =====
    data = fetch_data(TICKER)

    if data is None:
        print("⚠ Using fallback ETF")
        data = fetch_data(FALLBACK_TICKER)

    if data is None:
        print("❌ No data available")
        return

    vix_data = fetch_data(VIX_TICKER, "5d")

    current_price = get_last(data["Close"])

    if current_price is None:
        print("❌ Price fetch failed")
        return

    if vix_data is None:
        vix = 0.20
    else:
        vix_val = get_last(vix_data["Close"])
        vix = vix_val/100 if vix_val else 0.20

    # ===== RETURNS =====
    returns = np.log(data["Close"]/data["Close"].shift(1)).dropna()
    mu = returns.mean()
    hist_vol = returns.std()*np.sqrt(252)

    sigma = 0.7*vix + 0.3*hist_vol
    sigma_d = sigma/np.sqrt(252)

    # ===== MONTE CARLO =====
    paths = np.zeros((SIMULATIONS, DAYS))
    paths[:,0] = current_price

    for t in range(1,DAYS):
        z = np.random.randn(SIMULATIONS)
        paths[:,t] = paths[:,t-1]*np.exp((mu-0.5*sigma_d**2)+sigma_d*z)

    final_prices = paths[:,-1]
    mean_path = paths.mean(axis=0)

    p5,p25,p50,p75,p95 = np.percentile(paths,[5,25,50,75,95],axis=0)

    # ===== PROBABILITIES =====
    probs = {
        "Increase": prob(final_prices>current_price),
        "Decrease": prob(final_prices<current_price),
        "+2%": prob(final_prices>current_price*1.02),
        "-2%": prob(final_prices<current_price*0.98),
        "+5%": prob(final_prices>current_price*1.05),
        "-5%": prob(final_prices<current_price*0.95),
        "+10%": prob(final_prices>current_price*1.10),
        "-10%": prob(final_prices<current_price*0.90),
        "Above 25000": prob(final_prices>25000),
        "Below 23000": prob(final_prices<23000)
    }

    prob_html = "<table border='1'><tr><th>Scenario</th><th>Probability</th></tr>"
    for k,v in probs.items():
        color = "green" if ("+" in k or "Increase" in k or "Above" in k) else "red"
        prob_html += f"<tr><td>{k}</td><td style='color:{color};font-weight:bold'>{v}%</td></tr>"
    prob_html += "</table>"

    # ===== OPTIONS =====
    T = DAYS/252
    atm = round(current_price/50)*50

    call_bs = bs(current_price,atm,T,RISK_FREE,sigma,"call")
    put_bs = bs(current_price,atm,T,RISK_FREE,sigma,"put")

    call_mc = np.mean(np.maximum(final_prices-atm,0))*np.exp(-RISK_FREE*T)
    put_mc = np.mean(np.maximum(atm-final_prices,0))*np.exp(-RISK_FREE*T)

    # ===== STRIKES =====
    lower = round(np.percentile(final_prices,20)/50)*50
    upper = round(np.percentile(final_prices,80)/50)*50

    premium = call_bs + put_bs
    be_upper = upper + premium
    be_lower = lower - premium

    win_prob = prob((final_prices<upper)&(final_prices>lower))
    expected_pnl = np.mean(-(np.maximum(final_prices-upper,0))-(np.maximum(lower-final_prices,0)))
    rr = premium/(be_upper-current_price)

    vol_signal = "SELL OPTIONS" if vix > hist_vol else "BUY OPTIONS"

    # ===== TECHNICALS =====
    dma20 = data["Close"].rolling(20).mean()
    dma50 = data["Close"].rolling(50).mean()

    delta = data["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain/loss
    rsi = 100-(100/(1+rs))

    # ===== PRICE CHART =====
    fig_price = go.Figure()
    fig_price.add_trace(go.Scatter(x=data.index,y=data["Close"],name="Price"))
    fig_price.add_trace(go.Scatter(x=data.index,y=dma20,name="20DMA"))
    fig_price.add_trace(go.Scatter(x=data.index,y=dma50,name="50DMA"))

    fig_price.update_layout(title="Price + Moving Averages",
        paper_bgcolor='#050A0F',plot_bgcolor='#050A0F',
        font=dict(color="white"))

    # ===== RSI =====
    fig_rsi = go.Figure()
    fig_rsi.add_trace(go.Scatter(x=data.index,y=rsi,name="RSI"))
    fig_rsi.add_hline(y=70)
    fig_rsi.add_hline(y=30)
    fig_rsi.update_layout(title="RSI",
        paper_bgcolor='#050A0F',plot_bgcolor='#050A0F',
        font=dict(color="white"))

    # ===== MC BANDS =====
    x = np.arange(DAYS)
    fig_mc = go.Figure()

    fig_mc.add_trace(go.Scatter(x=x,y=p95,line=dict(width=0)))
    fig_mc.add_trace(go.Scatter(x=x,y=p5,fill='tonexty',fillcolor='rgba(0,180,255,0.08)',line=dict(width=0)))

    fig_mc.add_trace(go.Scatter(x=x,y=p75,line=dict(width=0)))
    fig_mc.add_trace(go.Scatter(x=x,y=p25,fill='tonexty',fillcolor='rgba(0,180,255,0.15)',line=dict(width=0)))

    fig_mc.add_trace(go.Scatter(x=x,y=mean_path,line=dict(color='cyan',width=3),name="Mean"))
    fig_mc.add_trace(go.Scatter(x=x,y=p5,line=dict(color='red',dash='dash'),name="P5"))
    fig_mc.add_trace(go.Scatter(x=x,y=p95,line=dict(color='green',dash='dash'),name="P95"))

    fig_mc.add_hline(y=current_price,line_dash="dash",line_color="white")

    fig_mc.update_layout(title="Monte Carlo Confidence Bands",
        xaxis_title="Trading Day",
        yaxis_title="Price (₹)",
        paper_bgcolor='#050A0F',
        plot_bgcolor='#050A0F',
        font=dict(color="white"))

    # ===== HISTOGRAM =====
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Histogram(x=final_prices))
    fig_hist.update_layout(title="Price Distribution",
        paper_bgcolor='#050A0F',plot_bgcolor='#050A0F',
        font=dict(color="white"))

    # ===== MC vs BS =====
    fig_bs = go.Figure()
    fig_bs.add_trace(go.Bar(name='MC',x=['Call','Put'],y=[call_mc,put_mc]))
    fig_bs.add_trace(go.Bar(name='BS',x=['Call','Put'],y=[call_bs,put_bs]))
    fig_bs.update_layout(barmode='group',
        title="MC vs Black-Scholes",
        paper_bgcolor='#050A0F',
        plot_bgcolor='#050A0F',
        font=dict(color="white"))

    # ===== HTML =====
    html = f"""
    <html><head><meta http-equiv="refresh" content="60"></head>
    <body style="background:#050A0F;color:white;font-family:Arial">

    <h2>Market Summary</h2>
    <p>Price: ₹{current_price:.2f}</p>
    <p>VIX: {vix*100:.2f}% | Vol: {sigma*100:.2f}%</p>
    <p>{vol_signal}</p>

    <h2>Probabilities</h2>
    {prob_html}

    <h2>Strategy</h2>
    <p>Sell {upper} CE & Sell {lower} PE</p>
    <p>Win Prob: {win_prob}% | Expected PnL: {expected_pnl:.2f} | RR: {rr:.2f}</p>

    <h2>Break-even</h2>
    <p>Upper BE: ₹{be_upper:.2f}</p>
    <p>Lower BE: ₹{be_lower:.2f}</p>

    <h2>Price Chart</h2>
    {fig_price.to_html(False)}

    <h2>RSI</h2>
    {fig_rsi.to_html(False)}

    <h2>Monte Carlo</h2>
    {fig_mc.to_html(False)}

    <h2>Distribution</h2>
    {fig_hist.to_html(False)}

    <h2>MC vs BS</h2>
    {fig_bs.to_html(False)}

    </body></html>
    """

    with open("dashboard.html","w",encoding="utf-8") as f:
        f.write(html)

    print("Updated Successfully")

# ================= LOOP =================
while True:
    run_dashboard()
    time.sleep(60)