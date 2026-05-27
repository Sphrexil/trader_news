"""Kronos 股价预测器封装。

封装 Kronos 模型的加载、推理和结果格式化。
使用延迟加载：首次调用 predict() 时才从 HuggingFace 加载模型。
"""

import logging
import os
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# 模型配置
MODEL_ID = "NeoQuasar/Kronos-small"
TOKENIZER_ID = "NeoQuasar/Kronos-Tokenizer-base"
MODEL_DIR = os.path.dirname(__file__)


class KronosStockPredictor:
    """Kronos 股票预测器。

    用法:
        pred = KronosStockPredictor()
        result = pred.predict(kline_df, pred_days=5)
        # result: list[dict] with open/high/low/close for each future day
    """

    def __init__(self):
        self._model = None
        self._tokenizer = None
        self._predictor = None
        self._loaded = False

    def _ensure_loaded(self):
        """延迟加载模型（首次调用时）。"""
        if self._loaded:
            return

        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
        import sys
        if MODEL_DIR not in sys.path:
            sys.path.insert(0, MODEL_DIR)

        from kronos_model.kronos import Kronos, KronosPredictor, KronosTokenizer

        logger.info("加载 Kronos Tokenizer from %s...", TOKENIZER_ID)
        self._tokenizer = KronosTokenizer.from_pretrained(TOKENIZER_ID)

        logger.info("加载 Kronos Model from %s...", MODEL_ID)
        self._model = Kronos.from_pretrained(MODEL_ID)

        self._predictor = KronosPredictor(
            self._model,
            self._tokenizer,
            device="cpu",
            max_context=512,
        )
        self._loaded = True
        logger.info("Kronos 模型就绪 (CPU)")

    def predict(self, kline_data: list[dict], pred_days: int = 5) -> dict[str, Any]:
        """预测股票未来价格走势。

        Args:
            kline_data: K线数据列表，每项含 {date, open, high, low, close, vol}
                        至少需要 30 条历史数据
            pred_days: 预测未来天数，默认 5

        Returns:
            {
                "predictions": [{day, open, high, low, close}, ...],
                "model": "Kronos-small",
                "history_days": N,
                "pred_days": M,
            }
        """
        if len(kline_data) < 30:
            return {
                "error": f"历史数据不足: {len(kline_data)} 条, 至少需要 30 条",
                "predictions": [],
            }

        try:
            self._ensure_loaded()
        except Exception as e:
            logger.exception("Kronos 模型加载失败")
            return {"error": f"模型加载失败: {e}", "predictions": []}

        # 只取最近 40 天，避免远古极端波动干扰预测
        kline_data = sorted(kline_data, key=lambda x: str(x.get("date", "")))
        kline_data = kline_data[-40:] if len(kline_data) > 40 else kline_data

        # 转换为 DataFrame
        df = pd.DataFrame(kline_data)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        df = df[["open", "high", "low", "close"]].astype(float)

        # 生成未来时间戳
        last_date = df.index[-1]
        future_dates = pd.date_range(
            start=last_date + pd.Timedelta(days=1),
            periods=pred_days,
            freq="B",  # 工作日
        )

        try:
            result_df = self._predictor.predict(
                df=df,
                x_timestamp=df.index,
                y_timestamp=future_dates,
                pred_len=pred_days,
                T=1.0,
                top_p=0.9,
                sample_count=1,
            )
        except Exception as e:
            logger.exception("Kronos 预测推理失败")
            return {"error": f"预测失败: {e}", "predictions": []}

        # 安全校验：预测值偏离当前价超过 40% 视为异常
        current_close = float(df["close"].iloc[-1])
        max_close = max(abs(float(r[3])) for r in result_df.values)
        if current_close > 0 and max_close > current_close * 1.5:
            return {
                "error": f"预测异常(偏离>50%)，模型可能受历史极端波动影响，跳过",
                "predictions": [],
            }
        if current_close > 0 and max_close < current_close * 0.5:
            return {
                "error": f"预测异常(偏离>50%)，模型可能受历史极端波动影响，跳过",
                "predictions": [],
            }

        # 格式化输出
        predictions = []
        for i, (dt, row) in enumerate(zip(future_dates, result_df.values)):
            predictions.append({
                "day": i + 1,
                "date": dt.strftime("%Y-%m-%d"),
                "open": round(float(row[0]), 2),
                "high": round(float(row[1]), 2),
                "low": round(float(row[2]), 2),
                "close": round(float(row[3]), 2),
            })

        return {
            "predictions": predictions,
            "model": "Kronos-small",
            "history_days": len(kline_data),
            "pred_days": pred_days,
        }


# 全局单例
_predictor: KronosStockPredictor | None = None


def get_kronos_predictor() -> KronosStockPredictor:
    global _predictor
    if _predictor is None:
        _predictor = KronosStockPredictor()
    return _predictor
