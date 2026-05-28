"""技术指标计算模块。纯 numpy/pandas 实现，不引入新依赖。

所有指标函数接受 pandas DataFrame（含 OHLCV 列），返回 dict。
"""

import numpy as np
import pandas as pd


def calc_ma(df: pd.DataFrame, periods: list[int] | None = None) -> dict:
    """计算移动均线及乖离率。

    Returns:
        {f"ma{p}": float, f"ma{p}_bias": float, ...}  — 均线值和乖离率(%)
    """
    if periods is None:
        periods = [5, 10, 20, 60]
    closes = df["close"].values.astype(float)
    if len(closes) == 0:
        return {}
    current = closes[-1]
    result = {}
    for p in periods:
        if len(closes) >= p:
            ma_val = float(np.mean(closes[-p:]))
            result[f"ma{p}"] = round(ma_val, 2)
            result[f"ma{p}_bias"] = round((current - ma_val) / ma_val * 100, 2)
        else:
            result[f"ma{p}"] = None
            result[f"ma{p}_bias"] = None
    # 均线排列判断
    available = [p for p in [5, 10, 20] if f"ma{p}" in result and result[f"ma{p}"] is not None]
    if len(available) >= 2:
        # 检查是否多头排列 (ma5 > ma10 > ma20) 或空头排列
        vals = [result[f"ma{p}"] for p in available]
        if all(vals[i] > vals[i + 1] for i in range(len(vals) - 1)):
            result["ma_alignment"] = "多头排列"
        elif all(vals[i] < vals[i + 1] for i in range(len(vals) - 1)):
            result["ma_alignment"] = "空头排列"
        else:
            result["ma_alignment"] = "交叉震荡"
    else:
        result["ma_alignment"] = "数据不足"
    return result


def calc_rsi(df: pd.DataFrame, period: int = 14) -> dict:
    """计算 RSI 相对强弱指标 (Wilder's smoothing)。

    Returns:
        {"rsi": float, "rsi_label": str}
    """
    closes = df["close"].values.astype(float)
    if len(closes) < period + 1:
        return {"rsi": None, "rsi_label": "数据不足"}

    deltas = np.diff(closes[-period - 1:])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    # Wilder's smoothing for the last value
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        rsi_val = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi_val = 100.0 - (100.0 / (1.0 + rs))

    if rsi_val > 70:
        label = "超买"
    elif rsi_val < 30:
        label = "超卖"
    elif rsi_val > 50:
        label = "偏强"
    else:
        label = "偏弱"

    return {"rsi": round(float(rsi_val), 1), "rsi_label": label}


def calc_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """计算 MACD 指标。

    Returns:
        {"dif": float, "dea": float, "macd": float, "macd_signal": str}
    """
    closes = df["close"].values.astype(float)
    min_len = slow + signal
    if len(closes) < min_len:
        return {"dif": None, "dea": None, "macd": None, "macd_signal": "数据不足"}

    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    dif = ema_fast - ema_slow
    dea = _ema(dif, signal)
    macd_bar = (dif - dea) * 2  # 柱 (A 股惯例乘 2)

    current_dif = float(dif[-1])
    current_dea = float(dea[-1])
    current_bar = float(macd_bar[-1])

    # 信号判断
    if len(dif) >= 2:
        if dif[-1] > dea[-1] and dif[-2] <= dea[-2]:
            macd_signal = "金叉"
        elif dif[-1] < dea[-1] and dif[-2] >= dea[-2]:
            macd_signal = "死叉"
        elif dif[-1] > dea[-1]:
            macd_signal = "多头"
        else:
            macd_signal = "空头"
    else:
        macd_signal = "数据不足"

    return {
        "dif": round(current_dif, 4),
        "dea": round(current_dea, 4),
        "macd": round(current_bar, 4),
        "macd_signal": macd_signal,
    }


def calc_bollinger(df: pd.DataFrame, period: int = 20, nbdev: float = 2.0) -> dict:
    """计算布林带。

    Returns:
        {"upper": float, "mid": float, "lower": float, "width_pct": float, "position": str}
    """
    closes = df["close"].values.astype(float)
    if len(closes) < period:
        return {"upper": None, "mid": None, "lower": None, "width_pct": None, "position": "数据不足"}

    recent = closes[-period:]
    mid = np.mean(recent)
    std = np.std(recent, ddof=0)
    upper = mid + nbdev * std
    lower = mid - nbdev * std
    current = closes[-1]

    width_pct = (upper - lower) / mid * 100 if mid > 0 else 0

    # 价格在布林带中的位置 (0~1)
    if upper > lower:
        pos_ratio = (current - lower) / (upper - lower)
        if pos_ratio > 1:
            position = "突破上轨"
        elif pos_ratio > 0.8:
            position = "上轨附近"
        elif pos_ratio < 0:
            position = "跌破下轨"
        elif pos_ratio < 0.2:
            position = "下轨附近"
        else:
            position = "中轨附近"
    else:
        position = "异常"

    return {
        "upper": round(float(upper), 2),
        "mid": round(float(mid), 2),
        "lower": round(float(lower), 2),
        "width_pct": round(float(width_pct), 1),
        "position": position,
    }


def calc_volume_ratio(df: pd.DataFrame, period: int = 5) -> dict:
    """计算量比（当日成交量 / 近N日均量）。

    Returns:
        {"vol_ratio": float, "vol_label": str}
    """
    vol_col = "volume" if "volume" in df.columns else "vol"
    if vol_col not in df.columns or len(df) < period + 1:
        return {"vol_ratio": None, "vol_label": "数据不足"}

    vols = pd.to_numeric(df[vol_col], errors="coerce").fillna(0).values
    current_vol = vols[-1]
    avg_vol = np.mean(vols[-period - 1:-1])

    if avg_vol == 0:
        ratio = 1.0
    else:
        ratio = current_vol / avg_vol

    if ratio > 3:
        label = "巨量"
    elif ratio > 2:
        label = "放量"
    elif ratio > 1.2:
        label = "温和放量"
    elif ratio > 0.8:
        label = "正常"
    elif ratio > 0.5:
        label = "缩量"
    else:
        label = "地量"

    return {"vol_ratio": round(float(ratio), 2), "vol_label": label}


def calc_atr(df: pd.DataFrame, period: int = 14) -> dict:
    """计算 ATR 平均真实波幅 (Wilder's smoothing)。

    Returns:
        {"atr": float, "atr_pct": float}
    """
    if len(df) < period + 1:
        return {"atr": None, "atr_pct": None}

    high = df["high"].values.astype(float)
    low = df["low"].values.astype(float)
    close = df["close"].values.astype(float)

    tr_list = []
    for i in range(1, len(close)):
        tr = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
        tr_list.append(tr)

    tr_array = np.array(tr_list[-period:])
    atr_val = np.mean(tr_array[:period])
    for i in range(period, len(tr_array)):
        atr_val = (atr_val * (period - 1) + tr_array[i]) / period

    current_close = close[-1]
    atr_pct = atr_val / current_close * 100 if current_close > 0 else 0

    return {"atr": round(float(atr_val), 4), "atr_pct": round(float(atr_pct), 2)}


def calc_all_indicators(df: pd.DataFrame) -> dict:
    """计算全部技术指标，返回汇总 dict。"""
    return {
        **calc_ma(df),
        **calc_rsi(df),
        **calc_macd(df),
        **calc_bollinger(df),
        **calc_volume_ratio(df),
        **calc_atr(df),
    }


def summarize_indicators(indicators: dict) -> str:
    """根据指标生成一句话技术面总结。"""
    parts = []
    rsi = indicators.get("rsi")
    rsi_label = indicators.get("rsi_label", "")
    if rsi is not None:
        parts.append(f"RSI={rsi}({rsi_label})")

    macd_signal = indicators.get("macd_signal", "")
    if macd_signal and macd_signal != "数据不足":
        parts.append(f"MACD {macd_signal}")

    ma_align = indicators.get("ma_alignment", "")
    if ma_align and ma_align != "数据不足":
        parts.append(ma_align)

    bb_pos = indicators.get("position", "")
    if bb_pos and bb_pos != "数据不足":
        parts.append(f"布林{bb_pos}")

    vol_label = indicators.get("vol_label", "")
    if vol_label and vol_label != "数据不足":
        parts.append(vol_label)

    return "；".join(parts) if parts else "指标数据不足"


# ── 内部工具函数 ──────────────────────────────────────


def _ema(data: np.ndarray, period: int) -> np.ndarray:
    """计算 EMA (指数移动平均)。"""
    alpha = 2.0 / (period + 1)
    result = np.zeros_like(data)
    result[0] = data[0]
    for i in range(1, len(data)):
        result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
    return result
