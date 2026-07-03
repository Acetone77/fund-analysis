"""业绩指标计算单元测试."""

import numpy as np
import pandas as pd
import pytest

from fund_analysis import metrics as m


@pytest.fixture
def up_nav() -> pd.Series:
    """模拟单边上涨净值：100 -> 150，252 个交易日."""
    dates = pd.date_range("2020-01-01", periods=252, freq="B")
    values = np.linspace(100, 150, 252)
    return pd.Series(values, index=dates)


@pytest.fixture
def sideways_nav() -> pd.Series:
    """模拟震荡净值."""
    dates = pd.date_range("2020-01-01", periods=252, freq="B")
    np.random.seed(42)
    daily_ret = np.random.normal(0.0005, 0.01, 252)
    values = 1.0 * np.cumprod(1 + daily_ret)
    return pd.Series(values, index=dates)


@pytest.fixture
def crash_nav() -> pd.Series:
    """模拟暴跌 + 恢复."""
    dates = pd.date_range("2020-01-01", periods=252, freq="B")
    values = np.ones(252)
    values[:63] = np.linspace(1.0, 1.5, 63)
    values[63:126] = np.linspace(1.5, 0.9, 63)
    values[126:] = np.linspace(0.9, 1.2, 126)
    return pd.Series(values, index=dates)


class TestCalcReturns:
    def test_up_trend(self, up_nav):
        r = m.calc_returns(up_nav)
        assert r["total_return"] == pytest.approx(0.5, abs=0.01)

    def test_empty_series(self):
        assert m.calc_returns(pd.Series()) == {}

    def test_single_value(self):
        assert m.calc_returns(pd.Series([1.0])) == {}


class TestCalcRisk:
    def test_up_trend_no_drawdown(self, up_nav):
        risk = m.calc_risk(up_nav)
        assert risk["max_drawdown"] == pytest.approx(0.0, abs=0.001)

    def test_crash_has_drawdown(self, crash_nav):
        risk = m.calc_risk(crash_nav)
        assert risk["max_drawdown"] < -0.3

    def test_var_range(self, sideways_nav):
        risk = m.calc_risk(sideways_nav)
        assert risk["var_95"] < 0
        assert risk["var_99"] < risk["var_95"]


class TestCalcSharpe:
    def test_positive_sharpe(self, up_nav):
        s = m.calc_sharpe(up_nav)
        assert s["sharpe_ratio"] > 0

    def test_win_rate_range(self, sideways_nav):
        s = m.calc_sharpe(sideways_nav)
        assert 0 <= s["win_rate"] <= 1


class TestMonthlyReturns:
    def test_returns_dataframe(self, sideways_nav):
        pivot = m.calc_monthly_returns(sideways_nav)
        assert not pivot.empty

    def test_yearly_returns(self):
        """需要至少 2 年数据才有年度收益."""
        dates = pd.date_range("2019-01-01", periods=756, freq="B")
        np.random.seed(42)
        daily_ret = np.random.normal(0.0005, 0.01, 756)
        values = 1.0 * np.cumprod(1 + daily_ret)
        nav = pd.Series(values, index=dates)
        yr = m.calc_yearly_returns(nav)
        assert not yr.empty
        assert "annual_return" in yr.columns


class TestCalcAll:
    def test_combined_result(self, sideways_nav):
        result = m.calc_all(sideways_nav)
        assert "total_return" in result
        assert "sharpe_ratio" in result
        assert "max_drawdown" in result
