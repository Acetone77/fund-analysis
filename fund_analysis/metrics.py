"""业绩指标计算引擎 — 纯函数，输入净值 Series，输出指标 dict."""

import numpy as np
import pandas as pd

TRADING_DAYS = 252
RISK_FREE_RATE = 0.025


def _annual_factor(freq: str) -> float:
    return {"D": TRADING_DAYS, "W": 52, "M": 12}.get(freq, TRADING_DAYS)


def calc_returns(nav_series: pd.Series, rf: float = RISK_FREE_RATE) -> dict:
    """收益类指标."""
    if len(nav_series) < 2:
        return {}

    nav = nav_series.dropna()
    total_return = float(nav.iloc[-1] / nav.iloc[0] - 1)
    years = (nav.index[-1] - nav.index[0]).days / 365.25
    annual_return = float((1 + total_return) ** (1 / years) - 1) if years > 0 else 0.0

    def _roll(days: int) -> float | None:
        if len(nav) < days:
            return None
        return float(nav.iloc[-1] / nav.iloc[-days] - 1)

    return {
        "total_return": round(total_return, 4),
        "annual_return": round(annual_return, 4),
        "return_1m": round(_roll(21), 4) if _roll(21) is not None else None,
        "return_3m": round(_roll(63), 4) if _roll(63) is not None else None,
        "return_6m": round(_roll(126), 4) if _roll(126) is not None else None,
        "return_1y": round(_roll(252), 4) if _roll(252) is not None else None,
        "return_3y_annual": round((1 + _roll(756)) ** (1 / 3) - 1, 4)
        if _roll(756) is not None and _roll(756) > -1
        else None,
        "excess_return": round(annual_return - rf, 4),
    }


def calc_risk(nav_series: pd.Series, rf: float = RISK_FREE_RATE) -> dict:
    """风险类指标."""
    if len(nav_series) < 2:
        return {}

    daily_returns = nav_series.pct_change().dropna()
    annual_vol = float(daily_returns.std() * np.sqrt(TRADING_DAYS))

    cummax = nav_series.expanding().max()
    drawdown = (nav_series - cummax) / cummax
    max_dd = float(drawdown.min())
    max_dd_idx = drawdown.idxmin()

    if pd.notna(max_dd_idx):
        peak_idx = nav_series[:max_dd_idx].idxmax()
        recovery = nav_series[max_dd_idx:]
        above_peak = recovery[recovery >= nav_series[peak_idx]]
        recovery_idx = above_peak.index[0] if len(above_peak) > 0 else None
    else:
        peak_idx, recovery_idx = None, None

    var_95 = float(daily_returns.quantile(0.05))
    var_99 = float(daily_returns.quantile(0.01))

    downside_returns = daily_returns[daily_returns < 0]
    downside_vol = (
        float(downside_returns.std() * np.sqrt(TRADING_DAYS))
        if len(downside_returns) > 0
        else 0.0
    )

    return {
        "annual_volatility": round(annual_vol, 4),
        "max_drawdown": round(max_dd, 4),
        "max_dd_start": str(peak_idx.date()) if peak_idx is not None else None,
        "max_dd_end": str(max_dd_idx.date()) if max_dd_idx is not None else None,
        "max_dd_recovery": str(recovery_idx.date()) if recovery_idx is not None else "未恢复",
        "max_dd_days": (max_dd_idx - peak_idx).days
        if peak_idx is not None and max_dd_idx is not None
        else None,
        "var_95": round(var_95, 4),
        "var_99": round(var_99, 4),
        "downside_volatility": round(downside_vol, 4),
    }


def calc_sharpe(nav_series: pd.Series, rf: float = RISK_FREE_RATE) -> dict:
    """风险调整收益指标."""
    if len(nav_series) < 2:
        return {}

    daily_returns = nav_series.pct_change().dropna()
    excess = daily_returns - rf / TRADING_DAYS

    sharpe = (
        float(excess.mean() / excess.std() * np.sqrt(TRADING_DAYS))
        if excess.std() > 0
        else 0.0
    )

    downside = daily_returns[daily_returns < rf / TRADING_DAYS]
    downside_std = downside.std()
    sortino = (
        float(excess.mean() / downside_std * np.sqrt(TRADING_DAYS))
        if downside_std > 0
        else 0.0
    )

    r = calc_returns(nav_series, rf)
    risk = calc_risk(nav_series, rf)
    max_dd = abs(risk.get("max_drawdown", 0))
    calmar = float(r.get("annual_return", 0) / max_dd) if max_dd > 0 else 0.0

    win_rate = float((daily_returns > 0).sum() / len(daily_returns))

    return {
        "sharpe_ratio": round(sharpe, 4),
        "sortino_ratio": round(sortino, 4),
        "calmar_ratio": round(calmar, 4),
        "win_rate": round(win_rate, 4),
    }


def calc_all(nav_series: pd.Series, rf: float = RISK_FREE_RATE) -> dict:
    """一站式计算所有指标."""
    return {
        **calc_returns(nav_series, rf),
        **calc_risk(nav_series, rf),
        **calc_sharpe(nav_series, rf),
    }


def calc_monthly_returns(nav_series: pd.Series) -> pd.DataFrame:
    """计算月度收益矩阵."""
    if len(nav_series) < 2:
        return pd.DataFrame()

    monthly = nav_series.resample("ME").last()
    monthly_ret = monthly.pct_change().dropna()
    monthly_ret.index = monthly_ret.index.to_period("M")

    df = monthly_ret.to_frame(name="return")
    df["year"] = df.index.year
    df["month"] = df.index.month

    pivot = df.pivot(index="year", columns="month", values="return")
    pivot.columns = [f"{m}月" for m in pivot.columns]
    return pivot


def calc_yearly_returns(nav_series: pd.Series) -> pd.DataFrame:
    """计算年度收益."""
    if len(nav_series) < 2:
        return pd.DataFrame()

    yearly = nav_series.resample("YE").last()
    yearly_ret = yearly.pct_change().dropna()
    yearly_ret.index = yearly_ret.index.year
    return yearly_ret.rename("annual_return").to_frame()
