"""测试技术指标计算模块。"""

import numpy as np
import pandas as pd
import pytest

from predictors.indicators import (
    calc_all_indicators,
    calc_atr,
    calc_bollinger,
    calc_ma,
    calc_macd,
    calc_rsi,
    calc_volume_ratio,
    summarize_indicators,
)


def make_sample_df(n: int = 100, trend: float = 0.001) -> pd.DataFrame:
    """生成模拟 OHLCV 数据。"""
    np.random.seed(42)
    base = 10.0
    closes = [base]
    vols = []
    for i in range(1, n):
        ret = trend + np.random.randn() * 0.02
        closes.append(closes[-1] * (1 + ret))
        vols.append(abs(np.random.randn()) * 1e6 + 5e5)
    closes = np.array(closes)
    highs = closes * (1 + np.abs(np.random.randn(n) * 0.01))
    lows = closes * (1 - np.abs(np.random.randn(n) * 0.01))
    opens = closes.copy()
    opens[1:] = closes[:-1] + np.random.randn(n - 1) * 0.005
    vols = np.array(vols + [vols[-1]]) if vols else np.full(n, 1e6)

    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": vols,
    })
    return df


class TestMA:
    def test_ma_basic(self):
        df = make_sample_df(100)
        result = calc_ma(df)
        assert result["ma5"] is not None
        assert result["ma10"] is not None
        assert result["ma20"] is not None
        assert isinstance(result["ma5_bias"], float)
        assert isinstance(result["ma_alignment"], str)

    def test_ma_insufficient_data(self):
        df = make_sample_df(3)
        result = calc_ma(df)
        assert result["ma5"] is None
        assert result["ma60"] is None

    def test_ma_custom_periods(self):
        df = make_sample_df(50)
        result = calc_ma(df, periods=[3, 7])
        assert result["ma3"] is not None
        assert result["ma7"] is not None
        assert "ma20" not in result


class TestRSI:
    def test_rsi_basic(self):
        df = make_sample_df(50, trend=0.005)
        result = calc_rsi(df)
        assert result["rsi"] is not None
        assert 0 <= result["rsi"] <= 100
        assert result["rsi_label"] in ("超买", "超卖", "偏强", "偏弱")

    def test_rsi_insufficient_data(self):
        df = make_sample_df(10)
        result = calc_rsi(df)
        assert result["rsi"] is None
        assert result["rsi_label"] == "数据不足"

    def test_rsi_uptrend(self):
        """上涨趋势中 RSI 应偏高。"""
        df = make_sample_df(50, trend=0.01)
        result = calc_rsi(df)
        assert result["rsi"] > 50


class TestMACD:
    def test_macd_basic(self):
        df = make_sample_df(100)
        result = calc_macd(df)
        assert result["dif"] is not None
        assert result["dea"] is not None
        assert result["macd"] is not None
        assert result["macd_signal"] in ("金叉", "死叉", "多头", "空头")

    def test_macd_insufficient_data(self):
        df = make_sample_df(20)
        result = calc_macd(df)
        assert result["dif"] is None


class TestBollinger:
    def test_bollinger_basic(self):
        df = make_sample_df(50)
        result = calc_bollinger(df)
        assert result["upper"] > result["mid"] > result["lower"]
        assert result["width_pct"] > 0
        assert isinstance(result["position"], str)

    def test_bollinger_insufficient_data(self):
        df = make_sample_df(10)
        result = calc_bollinger(df)
        assert result["upper"] is None


class TestVolumeRatio:
    def test_vol_ratio_basic(self):
        df = make_sample_df(30)
        result = calc_volume_ratio(df)
        assert result["vol_ratio"] is not None
        assert result["vol_ratio"] > 0
        assert isinstance(result["vol_label"], str)

    def test_vol_ratio_with_vol_column(self):
        df = make_sample_df(30)
        df["vol"] = df["volume"]
        del df["volume"]
        result = calc_volume_ratio(df)
        assert result["vol_ratio"] is not None


class TestATR:
    def test_atr_basic(self):
        df = make_sample_df(30)
        result = calc_atr(df)
        assert result["atr"] is not None
        assert result["atr"] > 0
        assert result["atr_pct"] > 0

    def test_atr_insufficient_data(self):
        df = make_sample_df(5)
        result = calc_atr(df)
        assert result["atr"] is None


class TestAllIndicators:
    def test_calc_all(self):
        df = make_sample_df(100)
        result = calc_all_indicators(df)
        assert "ma5" in result
        assert "rsi" in result
        assert "dif" in result
        assert "upper" in result
        assert "vol_ratio" in result
        assert "atr" in result

    def test_all_indicators_partial_data(self):
        """数据不足时部分指标为 None 但不会报错。"""
        df = make_sample_df(8)
        result = calc_all_indicators(df)
        assert result["rsi_label"] == "数据不足"
        assert result["ma10"] is None


class TestSummarize:
    def test_summarize(self):
        df = make_sample_df(100, trend=0.005)
        indicators = calc_all_indicators(df)
        summary = summarize_indicators(indicators)
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_summarize_insufficient(self):
        indicators = {"rsi": None, "rsi_label": "数据不足",
                       "macd_signal": "数据不足", "ma_alignment": "数据不足",
                       "position": "数据不足", "vol_label": "数据不足"}
        summary = summarize_indicators(indicators)
        assert summary == "指标数据不足"
