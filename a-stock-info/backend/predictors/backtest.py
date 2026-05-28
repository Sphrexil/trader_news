"""独立回测验证模块。

滚动窗口回测，对比 Kronos 模型与朴素统计基线。
"""

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def run_backtest(
    kline_data: list[dict],
    predictor,  # KronosStockPredictor 实例
    train_window: int = 40,
    pred_days: int = 5,
    step: int = 5,
    min_windows: int = 3,
) -> dict[str, Any]:
    """滚动窗口回测。

    Args:
        kline_data: 完整历史 K 线数据（按日期升序）
        predictor: KronosStockPredictor 实例
        train_window: 训练窗口大小（天）
        pred_days: 每窗口预测天数
        step: 滚动步长（天）
        min_windows: 最少需要生成的验证窗口数

    Returns:
        {
            "windows": int,                # 有效回测窗口数
            "kronos_direction_acc": str,   # Kronos 方向准确率
            "rw_direction_acc": str,       # 随机游走方向准确率
            "mean_direction_acc": str,     # 均值回归方向准确率
            "kronos_mape": float,          # Kronos MAPE
            "rw_mape": float,              # 随机游走 MAPE
            "mean_mape": float,            # 均值回归 MAPE
            "kronos_rmse": float,          # Kronos RMSE
            "rw_rmse": float,              # 随机游走 RMSE
            "mean_rmse": float,            # 均值回归 RMSE
            "kronos_win_rate": str,        # 战胜 RW 的窗口比例
            "window_details": [...],       # 各窗口详情
        }
    """
    if len(kline_data) < train_window + pred_days + step * (min_windows - 1):
        return {
            "windows": 0,
            "error": f"数据不足: 需要至少 {train_window + pred_days + step * (min_windows - 1)} 条, 实际 {len(kline_data)} 条",
        }

    kline_data = sorted(kline_data, key=lambda x: str(x.get("date", "")))
    close_prices = np.array([float(d["close"]) for d in kline_data])

    total = len(kline_data)
    windows = []
    start = 0
    while start + train_window + pred_days <= total:
        train_end = start + train_window
        test_end = train_end + pred_days

        train_data = kline_data[start:train_end]
        test_data = kline_data[train_end:test_end]

        # 实际未来价格
        actuals = np.array([float(d["close"]) for d in test_data])
        current_close = float(train_data[-1]["close"])

        # ── Kronos 预测 ──
        kronos_preds = None
        try:
            result = predictor.predict(train_data, pred_days=pred_days)
            if "predictions" in result and result["predictions"]:
                kronos_preds = np.array([p["close"] for p in result["predictions"]])
        except Exception as e:
            logger.warning(f"回测窗口 [{start}:{train_end}] Kronos 预测失败: {e}")

        # ── 朴素基线 1: 随机游走 (明天 = 今天) ──
        rw_preds = np.full(pred_days, current_close)

        # ── 朴素基线 2: 均值回归 ──
        train_closes = np.array([float(d["close"]) for d in train_data])
        mean_preds = np.full(pred_days, np.mean(train_closes[-20:]))

        # 计算各模型指标
        window_result = {
            "train_range": f"{train_data[0]['date']}~{train_data[-1]['date']}",
            "test_range": f"{test_data[0]['date']}~{test_data[-1]['date']}",
            "current_price": round(current_close, 2),
            "actual_avg": round(float(np.mean(actuals)), 2),
            "kronos": _evaluate_predictions(kronos_preds, actuals, current_close),
            "rw": _evaluate_predictions(rw_preds, actuals, current_close),
            "mean": _evaluate_predictions(mean_preds, actuals, current_close),
        }
        windows.append(window_result)
        start += step

    if len(windows) < min_windows:
        return {"windows": len(windows), "error": f"有效窗口不足: {len(windows)} < {min_windows}"}

    return _summarize_windows(windows)


def _evaluate_predictions(
    preds: np.ndarray | None, actuals: np.ndarray, current: float
) -> dict:
    """评估单窗口的预测指标。"""
    if preds is None or len(preds) != len(actuals):
        return {"direction_acc": None, "mape": None, "rmse": None}

    # 方向准确率
    pred_dirs = np.sign(preds - current)
    actual_dirs = np.sign(actuals - current)
    correct = int(np.sum(pred_dirs == actual_dirs))
    total = len(actuals)
    direction_acc = f"{correct}/{total}"

    # MAPE
    mape = float(np.mean(np.abs((actuals - preds) / actuals)) * 100)

    # RMSE
    rmse = float(np.sqrt(np.mean((actuals - preds) ** 2)))

    return {
        "direction_acc": direction_acc,
        "mape": round(mape, 2),
        "rmse": round(rmse, 2),
    }


def _summarize_windows(windows: list[dict]) -> dict:
    """汇总所有窗口的回测结果。"""
    def _avg_acc(windows_list, model_key):
        """计算平均方向准确率（从 N/M 格式解析）。"""
        correct_total = 0
        total_total = 0
        for w in windows_list:
            acc_str = w.get(model_key, {}).get("direction_acc", "")
            if acc_str and "/" in acc_str:
                parts = acc_str.split("/")
                correct_total += int(parts[0])
                total_total += int(parts[1])
        if total_total == 0:
            return "N/A"
        return f"{correct_total / total_total * 100:.1f}%"

    def _avg_metric(windows_list, model_key, metric):
        vals = [w.get(model_key, {}).get(metric) for w in windows_list]
        vals = [v for v in vals if v is not None]
        return round(float(np.mean(vals)), 2) if vals else None

    # Kronos 战胜 RW 的窗口数
    kronos_wins = 0
    for w in windows:
        k_mape = w.get("kronos", {}).get("mape")
        rw_mape = w.get("rw", {}).get("mape")
        if k_mape is not None and rw_mape is not None and k_mape < rw_mape:
            kronos_wins += 1

    return {
        "windows": len(windows),
        "kronos_direction_acc": _avg_acc(windows, "kronos"),
        "rw_direction_acc": _avg_acc(windows, "rw"),
        "mean_direction_acc": _avg_acc(windows, "mean"),
        "kronos_mape": _avg_metric(windows, "kronos", "mape"),
        "rw_mape": _avg_metric(windows, "rw", "mape"),
        "mean_mape": _avg_metric(windows, "mean", "mape"),
        "kronos_rmse": _avg_metric(windows, "kronos", "rmse"),
        "rw_rmse": _avg_metric(windows, "rw", "rmse"),
        "mean_rmse": _avg_metric(windows, "mean", "rmse"),
        "kronos_win_rate": f"{kronos_wins}/{len(windows)}",
        "conclusion": _make_conclusion(
            _avg_acc(windows, "kronos"),
            _avg_acc(windows, "rw"),
            f"{kronos_wins}/{len(windows)}",
        ),
        "window_details": windows[:5],  # 最多保留 5 个窗口详情
    }


def _make_conclusion(kronos_acc: str, rw_acc: str, win_rate: str) -> str:
    """根据回测指标生成结论。"""
    try:
        k = float(kronos_acc.replace("%", ""))
        r = float(rw_acc.replace("%", ""))
    except (ValueError, AttributeError):
        return "回测数据不足以得出结论"

    wr = win_rate.split("/")
    wins = int(wr[0]) if len(wr) == 2 else 0
    total = int(wr[1]) if len(wr) == 2 else 1

    if k > r + 10 and wins / total >= 0.6:
        return f"模型显著优于随机游走 (方向准确率 +{k - r:.0f}%)"
    elif k > r + 5:
        return f"模型略优于随机游走 (方向准确率 +{k - r:.0f}%)"
    elif k > r:
        return "模型略优于随机游走，但优势不显著"
    elif wins / total >= 0.5:
        return "模型与随机游走相当，预测能力有限"
    else:
        return "模型弱于随机游走，不建议依赖单模型预测"
