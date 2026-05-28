"""预测器涨跌停约束测试。"""

from types import SimpleNamespace

import numpy as np
import pandas as pd

from predictors.kronos_predictor import KronosStockPredictor


def make_kline_rows(n: int = 40, close: float = 10.0, ts_code: str = "002409.SZ") -> list[dict]:
    rows = []
    for i, dt in enumerate(pd.date_range("2026-01-01", periods=n, freq="D")):
        rows.append({
            "ts_code": ts_code,
            "date": dt.strftime("%Y-%m-%d"),
            "open": close,
            "high": close * 1.02,
            "low": close * 0.98,
            "close": close,
            "volume": 1_000_000,
            "amount": 10_000_000,
        })
    return rows


def make_fake_result(pred_days: int, close: float = 20.0) -> pd.DataFrame:
    values = np.column_stack([
        np.full(pred_days, close),   # open
        np.full(pred_days, close),   # high
        np.full(pred_days, close),   # low
        np.full(pred_days, close),   # close
        np.full(pred_days, close),   # volume placeholder
        np.full(pred_days, close),   # amount placeholder
    ])
    return pd.DataFrame(values)


def test_price_limit_pct_by_code_and_name():
    assert KronosStockPredictor._get_price_limit_pct("002409.SZ") == 0.10
    assert KronosStockPredictor._get_price_limit_pct("300001.SZ") == 0.20
    assert KronosStockPredictor._get_price_limit_pct("688001.SH") == 0.20
    assert KronosStockPredictor._get_price_limit_pct("830001.BJ") == 0.30
    assert KronosStockPredictor._get_price_limit_pct("000001.SZ", "*ST 测试") == 0.05


def test_predict_clamps_daily_move_within_limit(monkeypatch):
    predictor = KronosStockPredictor()
    predictor._ensure_loaded = lambda: None
    predictor._predictor = SimpleNamespace(
        predict=lambda **kwargs: make_fake_result(kwargs["pred_len"], close=20.0)
    )
    monkeypatch.setattr(predictor, "_calc_volatility_temperature", lambda df: (0.7, "中波动"))
    monkeypatch.setattr(
        predictor,
        "_get_market_context",
        lambda ts_code, df: {
            "beta": 1.0,
            "index_trend_5d": 0.0,
            "index_trend_20d": 0.0,
            "market_factor": 1.0,
            "label": "大盘平稳",
        },
    )
    monkeypatch.setattr(predictor, "_lr_returns_predict", lambda df, pred_days: np.full(pred_days, 20.0))
    monkeypatch.setattr(predictor, "_ma_crossover_predict", lambda df, pred_days: np.full(pred_days, 20.0))

    result = predictor.predict(
        make_kline_rows(),
        pred_days=3,
        include_technical=False,
        backtest_windows=0,
        ts_code="002409.SZ",
        stock_name="雅克科技",
    )

    preds = result["predictions"]
    assert len(preds) == 3
    assert result["p1_meta"]["limit_label"] == "10%"
    for p in preds:
        assert p["pct_change"] <= 10.0
        assert p["pct_change"] >= -10.0
        assert p["high"] <= round(p["open"] * 1.1, 2) + 0.01
        assert p["low"] >= round(p["open"] * 0.9, 2) - 0.01
        assert p["limit_hit"] is True
