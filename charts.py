import plotly.express as px
import plotly.graph_objects as go


def oi_bar_chart(df, title):
    if df.empty:
        return None

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["Strike"],
        y=df["CE OI"],
        name="Call OI"
    ))

    fig.add_trace(go.Bar(
        x=df["Strike"],
        y=df["PE OI"],
        name="Put OI"
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Strike Price",
        yaxis_title="Open Interest",
        barmode="group",
        height=500
    )

    return fig


def change_oi_chart(df, title):
    if df.empty:
        return None

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["Strike"],
        y=df["CE Change OI"],
        name="Call Change OI"
    ))

    fig.add_trace(go.Bar(
        x=df["Strike"],
        y=df["PE Change OI"],
        name="Put Change OI"
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Strike Price",
        yaxis_title="Change in OI",
        barmode="group",
        height=500
    )

    return fig