import streamlit as st
from sector_rotation import sector_summary, sector_bar_chart, sector_strength_chart, sector_leaders_laggards
from market_heatmap import create_market_heatmap, create_top_movers_table, create_volume_spike_table
from relative_strength import create_relative_strength_table, rs_summary, rs_scatter_chart, top_outperformers_underperformers
from config import REFRESH_INTERVAL_SECONDS, INDEX_SYMBOLS, OPTION_CHAIN_SYMBOLS
from data_fetcher import get_yfinance_index_data, get_option_chain
from signal_engine import option_chain_summary, detect_option_activity
from charts import oi_bar_chart, change_oi_chart
from simple_alerts import scan_simple_market, only_active_alerts
from cash_scanner import scan_cash_market, get_live_alerts
from datetime import datetime
from zoneinfo import ZoneInfo
from futures_scanner import create_futures_buildup_table, futures_signal_summary, futures_buildup_chart, top_long_short_tables
from simple_alerts import scan_simple_market, only_active_alerts
@st.fragment(run_every="5s")
def live_simple_alerts_fragment(stock_limit):
    full_df = scan_simple_market(limit=stock_limit)
    alert_df = only_active_alerts(full_df)

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Stocks Scanned", len(full_df))
    c2.metric("Active Alerts", len(alert_df))
    c3.metric(
        "Huge Buying",
        len(alert_df[alert_df["Alert"].str.contains("Buying", case=False, na=False)])
    )
    c4.metric(
        "Huge Selling",
        len(alert_df[alert_df["Alert"].str.contains("Selling", case=False, na=False)])
    )

    st.caption("Auto-refreshing this section every 5 seconds only.")

    st.subheader("🔥 Active Market Alerts")

    if alert_df.empty:
        st.success("No major alert right now.")
    else:
        st.dataframe(alert_df, use_container_width=True, height=500)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🚀 Buying / High Breakout Alerts")
        buy_df = alert_df[
            alert_df["Alert"].str.contains("Buying|High", case=False, na=False)
        ]
        st.dataframe(buy_df, use_container_width=True, height=350)

    with col2:
        st.subheader("🔻 Selling / Low Breakdown Alerts")
        sell_df = alert_df[
            alert_df["Alert"].str.contains("Selling|Low", case=False, na=False)
        ]
        st.dataframe(sell_df, use_container_width=True, height=350)

    st.divider()

    st.subheader("Full Market Scan")
    st.dataframe(full_df, use_container_width=True, height=600)

st.set_page_config(
    page_title="FalconLite NSE Terminal",
    page_icon="📊",
    layout="wide"
)




st.sidebar.title("📊 FalconLite NSE")
page = st.sidebar.radio(
    "Select Module",
    [
        "Home Dashboard",
        "Simple Market Alerts",
        "Option Chain & OI",
        "Cash Market Scanner",
        "Live Alerts",
        "Market Heatmap",
        "Sector Rotation",
        "Futures Buildup Scanner",
        "Delivery Spike Scanner",
        "Relative Strength Scanner",
        "VWAP Scanner",
        "Breakout Scanner",
        "Backtesting",
        "Intraday Replay",
        "Strategy Engine",
        "Database"
    ]
)

st.sidebar.caption(f"Auto refresh: {REFRESH_INTERVAL_SECONDS} sec")

if page == "Home Dashboard":
    st.title("📊 FalconLite NSE Market Intelligence Terminal")
    st.caption("Free delayed-data prototype using NSE public data + yfinance")

    index_df = get_yfinance_index_data(INDEX_SYMBOLS)

    c1, c2, c3, c4 = st.columns(4)

    try:
        nifty = index_df[index_df["Index"] == "NIFTY"].iloc[0]
        banknifty = index_df[index_df["Index"] == "BANKNIFTY"].iloc[0]

        c1.metric("NIFTY", nifty["Price"], f'{nifty["Change %"]}%')
        c2.metric("BANKNIFTY", banknifty["Price"], f'{banknifty["Change %"]}%')
    except Exception:
        c1.metric("NIFTY", "NA")
        c2.metric("BANKNIFTY", "NA")

    scanner_df = scan_cash_market()
    alerts_df = get_live_alerts(scanner_df)

    c3.metric("Active Stock Alerts", len(alerts_df))
    c4.metric("Stocks Scanned", len(scanner_df))

    st.divider()

    st.subheader("🚨 Latest Alerts")

    if alerts_df.empty:
        st.success("No major buying/selling alert right now.")
    else:
        st.dataframe(alerts_df, use_container_width=True, height=350)

    st.subheader("📈 Cash Market Scanner Snapshot")
    st.dataframe(scanner_df, use_container_width=True, height=450)

elif page == "Simple Market Alerts":

    import time

    st.title("🚨 Simple Market Alert Screen")
    st.caption("Live scanner for buying/selling, breakouts and volume spikes")

    stock_limit = st.slider(
        "Number of stocks to scan",
        50,
        500,
        100,
        step=50
    )

    refresh_placeholder = st.empty()

    table_placeholder = st.empty()

    alert_placeholder = st.empty()

    while True:

        refresh_placeholder.info(
            f"Last Updated: {datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%d-%b-%Y %I:%M:%S %p IST')}"
        )

        full_df = scan_simple_market(limit=stock_limit)

        alert_df = only_active_alerts(full_df)

        with alert_placeholder.container():

            c1, c2, c3, c4 = st.columns(4)

            c1.metric("Stocks Scanned", len(full_df))

            c2.metric("Active Alerts", len(alert_df))

            c3.metric(
                "Huge Buying",
                len(
                    alert_df[
                        alert_df["Alert"].str.contains(
                            "Buying",
                            case=False,
                            na=False
                        )
                    ]
                )
            )

            c4.metric(
                "Huge Selling",
                len(
                    alert_df[
                        alert_df["Alert"].str.contains(
                            "Selling",
                            case=False,
                            na=False
                        )
                    ]
                )
            )

        with table_placeholder.container():

            st.subheader("🔥 Active Market Alerts")

            if alert_df.empty:
                st.success("No major alert right now.")

            else:
                st.dataframe(
                    alert_df,
                    use_container_width=True,
                    height=500
                )

elif page == "Option Chain & OI":
    st.title("📌 Option Chain & OI Analysis")

    selected_symbol = st.selectbox("Select Index", OPTION_CHAIN_SYMBOLS, index=0)

    option_df = get_option_chain(selected_symbol)
    summary = option_chain_summary(option_df)

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("PCR", summary["pcr"])
    c2.metric("Market View", summary["market_view"])
    c3.metric("Total Call OI", f'{summary["total_call_oi"]:,}')
    c4.metric("Total Put OI", f'{summary["total_put_oi"]:,}')
    c5.metric("Max Pain Zone", f'{summary["max_put_oi_strike"]} - {summary["max_call_oi_strike"]}')

    tab1, tab2, tab3 = st.tabs(["Activity Scanner", "OI Charts", "Raw Option Chain"])

    with tab1:
        activity_df = detect_option_activity(option_df)
        st.dataframe(activity_df, use_container_width=True, height=550)

    with tab2:
        oi_fig = oi_bar_chart(option_df, f"{selected_symbol} Call vs Put OI")
        change_fig = change_oi_chart(option_df, f"{selected_symbol} Change in OI")

        if oi_fig:
            st.plotly_chart(oi_fig, use_container_width=True)

        if change_fig:
            st.plotly_chart(change_fig, use_container_width=True)

    with tab3:
        st.dataframe(option_df, use_container_width=True, height=600)


elif page == "Cash Market Scanner":
    st.title("💹 Cash Market Scanner")
    st.caption("Scans selected NSE stocks using 5-minute delayed/free data")

    scanner_df = scan_cash_market()

    st.dataframe(scanner_df, use_container_width=True, height=700)


elif page == "Live Alerts":
    st.title("🚨 Live Alerts")

    scanner_df = scan_cash_market()
    alerts_df = get_live_alerts(scanner_df)

    if alerts_df.empty:
        st.success("No major buying/selling or volume spike alert right now.")
    else:
        for _, row in alerts_df.iterrows():
            signal = row["Signal"]

            text = (
                f"{row['Symbol']} — {row['Signal']} | "
                f"Price: {row['Price']} | "
                f"Day Change: {row.get('Day Change %', 'NA')}% | "
                f"5m Change: {row['5m Change %']}% | "
                f"Volume Ratio: {row['Volume Ratio']}x | "
                f"Strength: {row['Strength']}/100"
            )

            if "Buying" in signal or "Positive" in signal:
                st.success("🚀 " + text)
            elif "Selling" in signal or "Negative" in signal:
                st.error("🔻 " + text)
            else:
                st.warning("⚠️ " + text)

        st.dataframe(alerts_df, use_container_width=True, height=500)


elif page == "Market Heatmap":
    st.title("🔥 Market Heatmap")
    st.caption("Market-wide visual scanner based on price movement, volume spike and alert strength")

    scanner_df = scan_cash_market()

    if scanner_df.empty:
        st.error("No scanner data available right now.")
    else:
        fig = create_market_heatmap(scanner_df)

        if fig:
            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        col1, col2 = st.columns(2)

        gainers, losers = create_top_movers_table(scanner_df)

        with col1:
            st.subheader("🚀 Top Gainers")
            st.dataframe(
                gainers[
                    [
                        "Symbol",
                        "Price",
                        "Day Change %",
                        "5m Change %",
                        "Volume Ratio",
                        "Signal",
                        "Strength"
                    ]
                ],
                use_container_width=True,
                height=450
            )

        with col2:
            st.subheader("🔻 Top Losers")
            st.dataframe(
                losers[
                    [
                        "Symbol",
                        "Price",
                        "Day Change %",
                        "5m Change %",
                        "Volume Ratio",
                        "Signal",
                        "Strength"
                    ]
                ],
                use_container_width=True,
                height=450
            )

        st.divider()

        st.subheader("⚡ Top Volume Spikes")

        volume_df = create_volume_spike_table(scanner_df)

        st.dataframe(
            volume_df[
                [
                    "Symbol",
                    "Price",
                    "Day Change %",
                    "5m Change %",
                    "Volume Ratio",
                    "Signal",
                    "Strength",
                    "Time"
                ]
            ],
            use_container_width=True,
            height=500
        )
elif page == "Simple Market Alerts":
    st.title("🚨 Simple Market Alert Screen")
    st.caption("Shows huge buying/selling, day high/low and week high/low breakouts")

    stock_limit = st.slider("Number of stocks to scan", 50, 500, 100, step=50)

    full_df = scan_simple_market(limit=stock_limit)
    alert_df = only_active_alerts(full_df)

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Stocks Scanned", len(full_df))
    c2.metric("Active Alerts", len(alert_df))
    c3.metric(
        "Huge Buying",
        len(alert_df[alert_df["Alert"].str.contains("Buying", case=False, na=False)])
    )
    c4.metric(
        "Huge Selling",
        len(alert_df[alert_df["Alert"].str.contains("Selling", case=False, na=False)])
    )

    st.divider()

    st.subheader("🔥 Active Market Alerts")

    if alert_df.empty:
        st.success("No major alert right now.")
    else:
        st.dataframe(alert_df, use_container_width=True, height=500)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🚀 Buying / High Breakout Alerts")

        buy_df = alert_df[
            alert_df["Alert"].str.contains(
                "Buying|High",
                case=False,
                na=False
            )
        ]

        st.dataframe(
            buy_df,
            use_container_width=True,
            height=400
        )

    with col2:
        st.subheader("🔻 Selling / Low Breakdown Alerts")

        sell_df = alert_df[
            alert_df["Alert"].str.contains(
                "Selling|Low",
                case=False,
                na=False
            )
        ]

        st.dataframe(
            sell_df,
            use_container_width=True,
            height=400
        )

    st.divider()

    st.subheader("Full Market Scan")

    st.dataframe(
        full_df,
        use_container_width=True,
        height=600
    )

elif page == "Sector Rotation":
    st.title("🔄 Sector Rotation")
    st.caption("Tracks sector leadership, weakness, volume pressure and buying/selling concentration")

    scanner_df = scan_cash_market()

    if scanner_df.empty:
        st.error("No scanner data available right now.")
    else:
        summary_df = sector_summary(scanner_df)

        c1, c2, c3, c4 = st.columns(4)

        try:
            top_sector = summary_df.sort_values("Avg_Day_Change", ascending=False).iloc[0]
            weak_sector = summary_df.sort_values("Avg_Day_Change", ascending=True).iloc[0]
            active_sector = summary_df.sort_values("Avg_Strength", ascending=False).iloc[0]

            c1.metric("Leading Sector", top_sector["Sector"], f'{top_sector["Avg_Day_Change"]}%')
            c2.metric("Weakest Sector", weak_sector["Sector"], f'{weak_sector["Avg_Day_Change"]}%')
            c3.metric("Most Active Sector", active_sector["Sector"], f'{active_sector["Avg_Strength"]}/100')
            c4.metric("Sectors Tracked", len(summary_df))

        except Exception:
            c1.metric("Leading Sector", "NA")
            c2.metric("Weakest Sector", "NA")
            c3.metric("Most Active Sector", "NA")
            c4.metric("Sectors Tracked", 0)

        st.divider()

        fig1 = sector_bar_chart(summary_df)
        fig2 = sector_strength_chart(summary_df)

        if fig1:
            st.plotly_chart(fig1, use_container_width=True)

        if fig2:
            st.plotly_chart(fig2, use_container_width=True)

        st.divider()

        st.subheader("Sector Summary Table")
        st.dataframe(summary_df, use_container_width=True, height=450)

        st.divider()

        leaders, laggards = sector_leaders_laggards(scanner_df)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🚀 Sector Leaders")
            st.dataframe(
                leaders[
                    [
                        "Symbol",
                        "Sector",
                        "Price",
                        "Day Change %",
                        "5m Change %",
                        "Volume Ratio",
                        "Signal",
                        "Strength"
                    ]
                ],
                use_container_width=True,
                height=500
            )

        with col2:
            st.subheader("🔻 Sector Laggards")
            st.dataframe(
                laggards[
                    [
                        "Symbol",
                        "Sector",
                        "Price",
                        "Day Change %",
                        "5m Change %",
                        "Volume Ratio",
                        "Signal",
                        "Strength"
                    ]
                ],
                use_container_width=True,
                height=500
            )

elif page == "Futures Buildup Scanner":
    st.title("📊 Futures Buildup Scanner")
    st.caption("Free-data proxy for long buildup, short buildup, short covering and long unwinding")

    scanner_df = scan_cash_market()

    if scanner_df.empty:
        st.error("No scanner data available right now.")
    else:
        futures_df = create_futures_buildup_table(scanner_df)
        summary_df = futures_signal_summary(futures_df)

        long_count = len(futures_df[futures_df["Futures Signal"] == "Long Buildup Proxy"])
        short_count = len(futures_df[futures_df["Futures Signal"] == "Short Buildup Proxy"])
        covering_count = len(futures_df[futures_df["Futures Signal"] == "Short Covering Proxy"])
        unwind_count = len(futures_df[futures_df["Futures Signal"] == "Long Unwinding Proxy"])

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Long Buildup Proxy", long_count)
        c2.metric("Short Buildup Proxy", short_count)
        c3.metric("Short Covering Proxy", covering_count)
        c4.metric("Long Unwinding Proxy", unwind_count)

        st.info(
            "Because this version uses free yfinance/NSE public data, this is a futures-like proxy. "
            "True futures OI requires authorised F&O data feed or broker API."
        )

        st.divider()

        fig = futures_buildup_chart(futures_df)

        if fig:
            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        st.subheader("Futures Signal Summary")
        st.dataframe(summary_df, use_container_width=True, height=350)

        st.divider()

        tab_a, tab_b, tab_c, tab_d, tab_e = st.tabs(
            [
                "All Futures Proxy Signals",
                "Long Buildup",
                "Short Buildup",
                "Short Covering",
                "Long Unwinding"
            ]
        )

        long_df, short_df, cover_df, unwind_df = top_long_short_tables(futures_df)

        with tab_a:
            st.dataframe(futures_df, use_container_width=True, height=600)

        with tab_b:
            st.dataframe(long_df, use_container_width=True, height=500)

        with tab_c:
            st.dataframe(short_df, use_container_width=True, height=500)

        with tab_d:
            st.dataframe(cover_df, use_container_width=True, height=500)

        with tab_e:
            st.dataframe(unwind_df, use_container_width=True, height=500)


elif page == "Delivery Spike Scanner":
    st.title("📦 Delivery Spike Scanner")
    st.caption("Free-data proxy for delivery spike, accumulation and distribution activity")

    scanner_df = scan_cash_market()

    if scanner_df.empty:
        st.error("No scanner data available right now.")
    else:
        delivery_df = create_delivery_table(scanner_df)
        summary_df = delivery_summary(delivery_df)

        accumulation_df, distribution_df = top_accumulation_distribution(delivery_df)

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Accumulation Stocks", len(accumulation_df))
        c2.metric("Distribution Stocks", len(distribution_df))
        c3.metric("Highest Volume Ratio", delivery_df["Volume Ratio"].max())
        c4.metric("Strongest Delivery Score", delivery_df["Delivery Strength"].max())

        st.info(
            "This is a delivery-like proxy using free intraday data. "
            "Actual NSE delivery quantity is normally available end-of-day."
        )

        st.divider()

        fig = delivery_chart(delivery_df)

        if fig:
            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        st.subheader("Delivery Signal Summary")
        st.dataframe(summary_df, use_container_width=True, height=350)

        st.divider()

        tab1, tab2, tab3 = st.tabs(
            [
                "All Delivery Signals",
                "Accumulation",
                "Distribution"
            ]
        )

        with tab1:
            st.dataframe(delivery_df, use_container_width=True, height=600)

        with tab2:
            st.dataframe(accumulation_df, use_container_width=True, height=500)

        with tab3:
            st.dataframe(distribution_df, use_container_width=True, height=500)

elif page == "Relative Strength Scanner":
    st.title("💪 Relative Strength Scanner")
    st.caption("Ranks stocks outperforming or underperforming NIFTY using price movement and volume pressure")

    scanner_df = scan_cash_market()
    index_df = get_yfinance_index_data(INDEX_SYMBOLS)

    try:
        nifty_change = float(index_df[index_df["Index"] == "NIFTY"].iloc[0]["Change %"])
    except Exception:
        nifty_change = 0

    if scanner_df.empty:
        st.error("No scanner data available right now.")
    else:
        rs_df = create_relative_strength_table(scanner_df, nifty_change)
        summary_df = rs_summary(rs_df)

        outperformers, underperformers = top_outperformers_underperformers(rs_df)

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("NIFTY Change", f"{nifty_change}%")
        c2.metric("Strong Outperformers", len(rs_df[rs_df["RS Signal"] == "Strong Outperformer"]))
        c3.metric("Strong Underperformers", len(rs_df[rs_df["RS Signal"] == "Strong Underperformer"]))
        c4.metric("Highest RS Score", rs_df["RS Score"].max())

        st.divider()

        fig = rs_scatter_chart(rs_df)

        if fig:
            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        st.subheader("Relative Strength Summary")
        st.dataframe(summary_df, use_container_width=True, height=350)

        st.divider()

        tab1, tab2, tab3 = st.tabs(
            [
                "All Relative Strength Signals",
                "Outperformers",
                "Underperformers"
            ]
        )

        common_cols = [
            "Symbol",
            "Price",
            "Day Change %",
            "Benchmark Change %",
            "Relative Strength %",
            "Volume Ratio",
            "RS Signal",
            "RS Score",
            "Signal",
            "Time"
        ]

        with tab1:
            st.dataframe(rs_df[common_cols], use_container_width=True, height=600)

        with tab2:
            st.dataframe(outperformers[common_cols], use_container_width=True, height=500)

        with tab3:
            st.dataframe(underperformers[common_cols], use_container_width=True, height=500)

elif page == "VWAP Scanner":
    st.title("📍 VWAP Scanner")
    st.warning("Next module to code: price above/below VWAP and VWAP breakout alerts.")


elif page == "Breakout Scanner":
    st.title("🚀 Breakout Scanner")
    st.warning("Next module to code: day high breakout, range breakout, volume breakout.")


elif page == "Backtesting":
    st.title("🧪 Strategy Backtesting")
    st.warning("Next module to code: test scanner signals on historical candles.")


elif page == "Intraday Replay":
    st.title("⏪ Intraday Replay")
    st.warning("Next module to code: replay stored market snapshots candle by candle.")


elif page == "Strategy Engine":
    st.title("⚙️ Strategy Engine")
    st.warning("Next module to code: rule-based strategy builder.")


elif page == "Database":
    st.title("🗄️ Historical Signal Database")
    st.warning("Next module to code: save alerts, scanner snapshots and signal history.")