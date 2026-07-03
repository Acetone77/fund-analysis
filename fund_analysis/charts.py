"""图表生成 — Plotly 图表，输入 DataFrame，输出 Figure."""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

COLORS = px.colors.qualitative.Plotly
FONT = {"family": "Microsoft YaHei, SimHei, sans-serif", "size": 13}
TEMPLATE = "plotly_white"


def _base_layout(fig: go.Figure, title: str, xlabel: str = "", ylabel: str = "") -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=18, family=FONT["family"])),
        font=FONT,
        template=TEMPLATE,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title=xlabel,
        yaxis_title=ylabel,
    )
    return fig


# ── 净值走势图 ──────────────────────────────────────────────

def nav_chart(df: pd.DataFrame, fund_name: str = "") -> go.Figure:
    """净值走势图，标记最大回撤区间."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df["nav"], mode="lines", name="单位净值",
        line=dict(color=COLORS[0], width=2),
        hovertemplate="%{x|%Y-%m-%d}<br>净值: %{y:.4f}<extra></extra>",
    ))
    if "acc_nav" in df.columns and not df["acc_nav"].equals(df["nav"]):
        fig.add_trace(go.Scatter(
            x=df.index, y=df["acc_nav"], mode="lines", name="累计净值",
            line=dict(color=COLORS[1], width=1.5, dash="dash"),
            hovertemplate="%{x|%Y-%m-%d}<br>累计: %{y:.4f}<extra></extra>",
        ))

    from fund_analysis.metrics import calc_risk
    risk = calc_risk(df["nav"])
    start = risk.get("max_dd_start")
    end = risk.get("max_dd_end")
    if start and end:
        fig.add_vrect(x0=start, x1=end, fillcolor="red", opacity=0.08,
                      annotation_text=f"最大回撤 {risk['max_drawdown']:.2%}",
                      annotation_position="top left")

    title = f"{fund_name} 净值走势" if fund_name else "净值走势"
    return _base_layout(fig, title, "日期", "净值")


# ── 回撤曲线图 ──────────────────────────────────────────────

def drawdown_chart(df: pd.DataFrame, fund_name: str = "") -> go.Figure:
    """回撤曲线（水面图）."""
    nav = df["nav"]
    cummax = nav.expanding().max()
    drawdown = (nav - cummax) / cummax

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=drawdown.index, y=drawdown * 100, mode="lines", name="回撤",
        fill="tozeroy", fillcolor="rgba(239, 68, 68, 0.15)",
        line=dict(color=COLORS[3], width=1.5),
        hovertemplate="%{x|%Y-%m-%d}<br>回撤: %{y:.2f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line=dict(color="gray", width=0.5, dash="dot"))

    title = f"{fund_name} 回撤曲线" if fund_name else "回撤曲线"
    fig = _base_layout(fig, title, "日期", "回撤 (%)")
    fig.update_layout(yaxis=dict(ticksuffix="%"))
    return fig


# ── 多基金对比图 ────────────────────────────────────────────

def comparison_chart(funds_data: dict[str, pd.DataFrame], column: str = "nav",
                     normalize: bool = True) -> go.Figure:
    """多基金归一化对比."""
    fig = go.Figure()
    for i, (name, df) in enumerate(funds_data.items()):
        if df.empty:
            continue
        series = df[column].dropna()
        if normalize:
            series = series / series.iloc[0]
        fig.add_trace(go.Scatter(
            x=series.index, y=series, mode="lines", name=name,
            line=dict(color=COLORS[i % len(COLORS)], width=2),
            hovertemplate="%{x|%Y-%m-%d}<br>净值: %{y:.4f}<extra></extra>",
        ))
    title = "归一化净值对比" if normalize else "净值对比"
    return _base_layout(fig, title, "日期", "归一化净值" if normalize else "净值")


# ── 风险-收益散点图 ─────────────────────────────────────────

def risk_return_scatter(funds_metrics: dict[str, dict]) -> go.Figure:
    """风险-收益散点图."""
    if not funds_metrics:
        return go.Figure()
    fig = go.Figure()
    for i, (name, m) in enumerate(funds_metrics.items()):
        fig.add_trace(go.Scatter(
            x=[m.get("annual_volatility", 0) * 100],
            y=[m.get("annual_return", 0) * 100],
            mode="markers+text", name=name, text=name, textposition="top center",
            marker=dict(size=max(12, m.get("sharpe_ratio", 0) * 8 + 10),
                        color=COLORS[i % len(COLORS)],
                        line=dict(width=2, color="white")),
            hovertemplate=f"<b>{name}</b><br>收益: %{{y:.2f}}%<br>波动: %{{x:.2f}}%<extra></extra>",
        ))
    fig = _base_layout(fig, "风险-收益散点图", "年化波动率 (%)", "年化收益率 (%)")
    fig.add_hline(y=0, line=dict(color="gray", width=0.5, dash="dot"))
    return fig


# ── 月度收益热力图 ──────────────────────────────────────────

def monthly_heatmap(pivot: pd.DataFrame, fund_name: str = "") -> go.Figure:
    """月度收益热力图."""
    if pivot.empty:
        return go.Figure()
    annot = pivot.map(lambda x: f"{x:.1%}" if pd.notna(x) else "")
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values, x=pivot.columns, y=pivot.index,
        text=annot.values, texttemplate="%{text}", textfont=dict(size=10),
        colorscale="RdYlGn", zmid=0,
        colorbar=dict(title="收益率", tickformat=".0%"),
        hovertemplate="%{y}年 %{x}<br>收益: %{z:.2%}<extra></extra>",
    ))
    title = f"{fund_name} 月度收益热力图" if fund_name else "月度收益热力图"
    fig = _base_layout(fig, title, "", "年份")
    fig.update_layout(yaxis=dict(dtick=1))
    return fig


# ── 年度收益柱状图 ──────────────────────────────────────────

def yearly_bar_chart(yearly_ret: pd.DataFrame, fund_name: str = "") -> go.Figure:
    """年度收益柱状图."""
    if yearly_ret.empty:
        return go.Figure()
    colors = yearly_ret["annual_return"].map(lambda x: "green" if x >= 0 else "red")
    fig = go.Figure(data=go.Bar(
        x=yearly_ret.index, y=yearly_ret["annual_return"] * 100,
        marker_color=colors,
        text=yearly_ret["annual_return"].map(lambda x: f"{x:.2%}"),
        textposition="outside",
        hovertemplate="%{x}年<br>收益: %{y:.2f}%<extra></extra>",
    ))
    title = f"{fund_name} 年度收益" if fund_name else "年度收益"
    fig = _base_layout(fig, title, "", "收益率")
    fig.update_layout(yaxis=dict(ticksuffix="%"))
    fig.add_hline(y=0, line=dict(color="gray", width=0.5))
    return fig


# ── 滚动收益曲线 ────────────────────────────────────────────

def rolling_return_chart(df: pd.DataFrame, window: int = 252, fund_name: str = "") -> go.Figure:
    """滚动年化收益率曲线."""
    nav = df["nav"].dropna()
    if len(nav) <= window:
        return go.Figure()
    rolling = nav.pct_change().rolling(window).apply(
        lambda x: (1 + x).prod() ** (252 / window) - 1
    ).dropna()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=rolling.index, y=rolling * 100, mode="lines", name="滚动收益",
        line=dict(color=COLORS[0], width=2),
        fill="tozeroy", fillcolor="rgba(59, 130, 246, 0.1)",
        hovertemplate="%{x|%Y-%m-%d}<br>滚动收益: %{y:.2f}%<extra></extra>",
    ))
    label = f"{window // 252}年" if window >= 252 else f"{window}日"
    title = f"{fund_name} 滚动{label}收益" if fund_name else f"滚动{label}收益"
    fig = _base_layout(fig, title, "日期", "年化收益率")
    fig.update_layout(yaxis=dict(ticksuffix="%"))
    fig.add_hline(y=0, line=dict(color="gray", width=0.5, dash="dot"))
    return fig
