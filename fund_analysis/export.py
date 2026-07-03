"""Excel 报告导出 — 多 sheet 报告."""

from io import BytesIO

import pandas as pd

from fund_analysis import db
from fund_analysis import metrics as m


def export_report(fund_code: str) -> BytesIO | None:
    """生成 Excel 报告（概览、净值明细、月度收益、年度收益、风险指标）."""
    info = db.get_fund(fund_code)
    df = db.get_nav_df(fund_code)
    if info is None or df.empty:
        return None

    indicators = m.calc_all(df["nav"])
    monthly = m.calc_monthly_returns(df["nav"])
    yearly = m.calc_yearly_returns(df["nav"])

    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Sheet 1: 概览
        overview = [
            ("基金代码", info["code"]),
            ("基金名称", info["name"]),
            ("基金类型", info.get("type", "")),
            ("成立日期", info.get("inception", "")),
            ("数据区间", f"{df.index[0].date()} ~ {df.index[-1].date()}"),
            ("", ""),
            ("累计收益率", _pct(indicators.get("total_return"))),
            ("年化收益率", _pct(indicators.get("annual_return"))),
            ("超额收益 (vs 无风险)", _pct(indicators.get("excess_return"))),
            ("", ""),
            ("年化波动率", _pct(indicators.get("annual_volatility"))),
            ("最大回撤", _pct(indicators.get("max_drawdown"))),
            ("最大回撤开始", indicators.get("max_dd_start", "")),
            ("最大回撤结束", indicators.get("max_dd_end", "")),
            ("回撤恢复日期", indicators.get("max_dd_recovery", "")),
            ("", ""),
            ("Sharpe Ratio", _num(indicators.get("sharpe_ratio"))),
            ("Sortino Ratio", _num(indicators.get("sortino_ratio"))),
            ("Calmar Ratio", _num(indicators.get("calmar_ratio"))),
            ("胜率", _pct(indicators.get("win_rate"))),
            ("", ""),
            ("近 1 月收益", _pct(indicators.get("return_1m"))),
            ("近 3 月收益", _pct(indicators.get("return_3m"))),
            ("近 6 月收益", _pct(indicators.get("return_6m"))),
            ("近 1 年收益", _pct(indicators.get("return_1y"))),
        ]
        pd.DataFrame(overview, columns=["指标", "数值"]).to_excel(
            writer, sheet_name="概览", index=False
        )

        # Sheet 2: 净值明细
        edf = df.copy()
        edf.index = edf.index.strftime("%Y-%m-%d")
        edf["nav"] = edf["nav"].round(4)
        if "acc_nav" in edf.columns:
            edf["acc_nav"] = edf["acc_nav"].round(4)
        if "daily_return" in edf.columns:
            edf["daily_return"] = edf["daily_return"].round(6)
        edf.reset_index().rename(columns={"index": "date"}).to_excel(
            writer, sheet_name="净值明细", index=False
        )

        # Sheet 3 & 4
        if not monthly.empty:
            monthly.to_excel(writer, sheet_name="月度收益")
        if not yearly.empty:
            yearly.to_excel(writer, sheet_name="年度收益")

        # Sheet 5: 风险指标
        risk = [
            ("年化波动率", _pct(indicators.get("annual_volatility"))),
            ("下行波动率", _pct(indicators.get("downside_volatility"))),
            ("最大回撤", _pct(indicators.get("max_drawdown"))),
            ("VaR (95%)", _pct(indicators.get("var_95"))),
            ("VaR (99%)", _pct(indicators.get("var_99"))),
            ("Sharpe Ratio", _num(indicators.get("sharpe_ratio"))),
            ("Sortino Ratio", _num(indicators.get("sortino_ratio"))),
            ("Calmar Ratio", _num(indicators.get("calmar_ratio"))),
            ("胜率", _pct(indicators.get("win_rate"))),
        ]
        pd.DataFrame(risk, columns=["风险指标", "数值"]).to_excel(
            writer, sheet_name="风险指标", index=False
        )

    output.seek(0)
    return output


def _pct(val) -> str:
    if val is None:
        return "-"
    return f"{val * 100:.2f}%"


def _num(val) -> str:
    if val is None:
        return "-"
    return f"{val:.4f}"
