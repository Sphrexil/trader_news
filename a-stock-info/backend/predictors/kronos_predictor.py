"""Kronos 股价预测器封装。v2.2 升级版。

改进：
- 修复 LR 基线：从价格水平回归 → 对数收益率回归
- 移除固定种子：真正的蒙特卡洛采样
- 基于采样的置信区间：替代固定衰减公式
- Beta 大盘联动：替代固定四档系数
- 集成技术指标 + 独立回测模块
"""

import logging
import os
from typing import Any

import numpy as np
import pandas as pd

from .indicators import calc_all_indicators, summarize_indicators
from .backtest import run_backtest

logger = logging.getLogger(__name__)

MODEL_ID = "NeoQuasar/Kronos-small"
TOKENIZER_ID = "NeoQuasar/Kronos-Tokenizer-base"
MODEL_DIR = os.path.dirname(__file__)

# 多轮采样次数（每次内部 sample_count=3，共 MULTI_ROUNDS 次独立调用）
MULTI_ROUNDS = 3


class KronosStockPredictor:
    """Kronos 股票预测器（v2.2 增强版）。"""

    def __init__(self):
        self._model = None
        self._tokenizer = None
        self._predictor = None
        self._loaded = False

    def _ensure_loaded(self):
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
        self._predictor = KronosPredictor(self._model, self._tokenizer, device="cpu", max_context=512)
        self._loaded = True
        logger.info("Kronos 模型就绪 (CPU)")

    # ── P1-1: 波动率自适应 ────────────────────────────

    @staticmethod
    def _calc_volatility_temperature(df: pd.DataFrame, window: int = 20) -> tuple[float, str]:
        """根据近20天波动率自适应调整温度T。"""
        if len(df) < window:
            return 0.7, "默认"
        returns = df["close"].pct_change().dropna().tail(window)
        daily_std = returns.std()
        annual_vol = daily_std * np.sqrt(252) * 100
        if annual_vol > 60:
            return 0.9, f"高波动({annual_vol:.0f}%)"
        elif annual_vol > 30:
            return 0.7, f"中波动({annual_vol:.0f}%)"
        else:
            return 0.5, f"低波动({annual_vol:.0f}%)"

    # ── P1-2: 大盘联动 (Beta 增强版) ──────────────────

    @staticmethod
    def _get_market_context(ts_code: str, df: pd.DataFrame) -> dict:
        """获取大盘上下文：趋势 + Beta + 动态系数。

        Returns:
            {"beta": float, "index_trend_5d": float,
             "index_trend_20d": float, "market_factor": float, "label": str}
        """
        result = {"beta": 1.0, "index_trend_5d": 0.0, "index_trend_20d": 0.0,
                   "market_factor": 1.0, "label": "大盘数据不可用"}

        try:
            from datasources.manager import get_ds_manager
            ds = get_ds_manager()
            idx_code = "000001.SH" if ts_code.endswith(".SH") else "399001.SZ"

            # 获取 65 天指数数据（60 天用于 Beta + 5 天用于趋势）
            idx_rows = ds.get_daily_prices(
                idx_code,
                (pd.Timestamp.now() - pd.Timedelta(days=120)).strftime("%Y-%m-%d"),
                pd.Timestamp.now().strftime("%Y-%m-%d"),
            )
            if not idx_rows or len(idx_rows) < 10:
                return result

            idx_closes = np.array([float(r["close"]) for r in idx_rows])

            # 短期趋势 (5天)
            if len(idx_closes) >= 5:
                trend_5d = (idx_closes[-1] - idx_closes[-5]) / idx_closes[-5]
                result["index_trend_5d"] = round(float(trend_5d * 100), 2)

            # 中期趋势 (20天)
            if len(idx_closes) >= 20:
                trend_20d = (idx_closes[-1] - idx_closes[-20]) / idx_closes[-20]
                result["index_trend_20d"] = round(float(trend_20d * 100), 2)

            # Beta 计算 (需要 60+ 天)
            if len(df) >= 30 and len(idx_rows) >= 30:
                beta = KronosStockPredictor._calc_beta(df, idx_rows)
                result["beta"] = round(beta, 2)

            # 动态市场因子: market_factor = 1.0 + beta * trend_5d
            trend = result["index_trend_5d"] / 100.0
            result["market_factor"] = round(1.0 + result["beta"] * trend, 3)
            result["market_factor"] = max(0.75, min(1.25, result["market_factor"]))

            # 生成标签
            trend_val = result["index_trend_5d"]
            if trend_val > 2:
                direction = "强势"
            elif trend_val > 0:
                direction = "偏强"
            elif trend_val > -2:
                direction = "偏弱"
            else:
                direction = "弱势"
            result["label"] = f"大盘{direction}({trend_val:+.1f}%, Beta={result['beta']})"

        except Exception as e:
            logger.debug(f"获取大盘数据失败: {e}")

        return result

    @staticmethod
    def _calc_beta(stock_df: pd.DataFrame, index_rows: list[dict]) -> float:
        """计算个股相对大盘的 Beta 系数。"""
        try:
            s_closes = stock_df["close"].values.astype(float)
            i_closes = np.array([float(r["close"]) for r in index_rows])

            s_returns = np.diff(np.log(s_closes[-60:])) if len(s_closes) >= 61 else np.diff(np.log(s_closes))
            i_returns = np.diff(np.log(i_closes[-60:])) if len(i_closes) >= 61 else np.diff(np.log(i_closes))

            # 对齐长度
            min_len = min(len(s_returns), len(i_returns))
            if min_len < 10:
                return 1.0
            s_returns = s_returns[-min_len:]
            i_returns = i_returns[-min_len:]

            cov = np.cov(s_returns, i_returns)[0, 1]
            var = np.var(i_returns)
            return cov / var if var > 0 else 1.0
        except Exception:
            return 1.0

    @staticmethod
    def _get_price_limit_pct(ts_code: str, stock_name: str | None = None) -> float:
        """根据市场/板块/名称推断单日涨跌幅限制。"""
        name = (stock_name or "").upper()
        code = ts_code.upper()

        if "ST" in name:
            return 0.05

        if code.endswith(".BJ"):
            return 0.30

        if code.endswith(".SH"):
            if code.startswith(("688", "689")):
                return 0.20
            return 0.10

        if code.endswith(".SZ"):
            if code.startswith(("300", "301")):
                return 0.20
            return 0.10

        return 0.10

    # ── P1-3: 对数收益率线性回归基线 ───────────────────

    @staticmethod
    def _lr_returns_predict(df: pd.DataFrame, pred_days: int) -> np.ndarray:
        """用最近 20 天对数收益率做线性回归，预测未来 N 天价格。

        在收益率空间做回归（统计有效），然后反算回价格。
        """
        from sklearn.linear_model import LinearRegression
        closes = df["close"].values.astype(float)
        if len(closes) < 21:
            return np.full(pred_days, closes[-1])

        log_returns = np.diff(np.log(closes[-21:]))  # 20 个对数收益率
        X = np.arange(20).reshape(-1, 1)
        y = log_returns
        lr = LinearRegression().fit(X, y)
        future_X = np.arange(20, 20 + pred_days).reshape(-1, 1)
        pred_returns = lr.predict(future_X).flatten()

        # 对数收益率累积回价格
        last_price = closes[-1]
        prices = [last_price]
        for r in pred_returns:
            prices.append(prices[-1] * np.exp(np.clip(r, -0.5, 0.5)))
        return np.array(prices[1:])

    @staticmethod
    def _ma_crossover_predict(df: pd.DataFrame, pred_days: int) -> np.ndarray:
        """用移动平均交叉判断趋势方向，线性推未来N天。"""
        closes = df["close"].values.astype(float)
        if len(closes) < 10:
            return np.full(pred_days, closes[-1])
        ma5 = np.mean(closes[-5:])
        ma10 = np.mean(closes[-10:])
        slope = (ma5 - ma10) / ma10 * 100 if ma10 > 0 else 0
        last = closes[-1]
        return np.array([last * (1 + slope / 100 * (i + 1)) for i in range(pred_days)])

    # ── 主预测 ─────────────────────────────────────────

    def predict(self, kline_data: list[dict], pred_days: int = 5,
                include_technical: bool = True,
                backtest_windows: int = 0,
                ts_code: str = "",
                stock_name: str | None = None) -> dict[str, Any]:
        """预测未来股价走势。

        Args:
            kline_data: 历史 K 线数据（按日期升序）
            pred_days: 预测天数 (1-10)
            include_technical: 是否返回技术指标
            backtest_windows: 回测窗口数 (0=不回测, 性能考虑)

        Returns:
            预测结果 dict，含 predictions / backtest / technical_summary / market_context
        """
        if len(kline_data) < 30:
            return {"error": f"历史数据不足: {len(kline_data)} 条", "predictions": []}

        try:
            self._ensure_loaded()
        except Exception as e:
            return {"error": f"模型加载失败: {e}", "predictions": []}

        kline_data = sorted(kline_data, key=lambda x: str(x.get("date", "")))
        kline_data = kline_data[-40:] if len(kline_data) > 40 else kline_data

        df = pd.DataFrame(kline_data)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        cols = ["open", "high", "low", "close"]
        for c in ["volume", "vol", "amount"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
                if c not in cols:
                    cols.append(c)
        if "vol" in df.columns and "volume" not in df.columns:
            df["volume"] = df["vol"]
            cols.append("volume")
        if "amount" not in df.columns:
            df["amount"] = 0
            cols.append("amount")
        # 安全兜底：如果 amount 全为空/零 (如某些数据源不返回成交额)，
        # 用 volume × 均价 计算成交额
        if df["amount"].fillna(0).sum() == 0 and "volume" in df.columns:
            avg_price = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
            df["amount"] = df["volume"] * avg_price
        df = df[cols].astype(float)

        current_close = float(df["close"].iloc[-1])
        last_date = df.index[-1]
        future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=pred_days, freq="B")

        # ── P1-1: 波动率自适应温度 ──
        T, vol_label = self._calc_volatility_temperature(df)
        top_p = 0.85 if T > 0.7 else 0.75

        # ── P1-2: 大盘联动 (Beta 增强) ──
        ts_code = ts_code or (kline_data[0].get("ts_code", "") if kline_data else "")
        market_ctx = self._get_market_context(ts_code, df)
        limit_pct = self._get_price_limit_pct(ts_code, stock_name)

        # ── 多轮蒙特卡洛采样（移除固定种子） ──
        all_samples = []
        for round_idx in range(MULTI_ROUNDS):
            try:
                # 每轮使用独立的种子（基于真实随机），不做 manual_seed
                kronos_result = self._predictor.predict(
                    df=df, x_timestamp=df.index, y_timestamp=future_dates,
                    pred_len=pred_days, T=T, top_p=top_p, sample_count=3,
                )
                # kronos_result 返回的是 OHLCV 6列，取 close (index=3)
                closes = np.array([float(kronos_result.iloc[i, 3]) for i in range(pred_days)])
                all_samples.append(closes)
            except Exception as e:
                logger.warning(f"采样轮次 {round_idx + 1} 失败: {e}")
                continue

        if not all_samples:
            return {"error": "所有采样轮次均失败", "predictions": []}

        all_samples = np.array(all_samples)  # shape: (n_samples, pred_days)
        kronos_closes = np.mean(all_samples, axis=0)
        kronos_std = np.std(all_samples, axis=0, ddof=1) if all_samples.shape[0] >= 2 else np.zeros(pred_days)

        # ── P1-3: 多模型投票（用对数收益率 LR） ──
        try:
            lr_closes = self._lr_returns_predict(df, pred_days)
            ma_closes = self._ma_crossover_predict(df, pred_days)
            # 加权混合：Kronos 60% + LR 20% + MA 20%
            blended = kronos_closes * 0.6 + lr_closes * 0.2 + ma_closes * 0.2
            # 大盘联动微调
            mf = market_ctx["market_factor"]
            blended = current_close + (blended - current_close) * mf
            # 方向一致性
            kronos_dir = np.sign(kronos_closes[-1] - current_close)
            lr_dir = np.sign(lr_closes[-1] - current_close)
            ma_dir = np.sign(ma_closes[-1] - current_close)
            votes = [kronos_dir, lr_dir, ma_dir]
            consensus = sum(votes)
            up_votes = sum(1 for v in votes if v > 0)
            down_votes = sum(1 for v in votes if v < 0)
            if consensus >= 3:
                vote_label = "一致看多"
            elif consensus <= -3:
                vote_label = "一致看空"
            elif consensus > 0:
                vote_label = f"偏多({up_votes}多{down_votes}空)"
            elif consensus < 0:
                vote_label = f"偏空({up_votes}多{down_votes}空)"
            else:
                vote_label = f"分歧({up_votes}多{down_votes}空)"
        except Exception:
            blended = kronos_closes
            lr_closes = np.full(pred_days, current_close)
            ma_closes = np.full(pred_days, current_close)
            vote_label = "Kronos单模型"

        # 安全校验：偏离不超 ±50%
        max_c = max(abs(float(c)) for c in blended)
        if current_close > 0 and (max_c > current_close * 1.5 or max_c < current_close * 0.5):
            return {"error": "预测异常(偏离>50%)，跳过", "predictions": []}

        recent_range_pct = (
            ((df["high"] - df["low"]) / df["close"])
            .replace([np.inf, -np.inf], np.nan)
            .dropna()
            .tail(20)
            .mean()
        )
        if not np.isfinite(recent_range_pct) or recent_range_pct <= 0:
            recent_range_pct = 0.02
        wick_pct = float(np.clip(recent_range_pct * 0.35, 0.002, 0.025))

        # ── 格式化预测 ──
        predictions = []
        prev_close = current_close
        for i, dt in enumerate(future_dates):
            raw_close = float(blended[i])
            limit_up = prev_close * (1 + limit_pct)
            limit_down = prev_close * (1 - limit_pct)
            pred_close = float(np.clip(raw_close, limit_down, limit_up))
            pct = round((pred_close - prev_close) / prev_close * 100, 2)
            # 基于样本标准差的真实置信度
            if kronos_std[i] > 0 and current_close > 0:
                cv = kronos_std[i] / current_close  # 变异系数
                confidence = round(max(0.1, 1.0 - cv * 5), 2)
            else:
                confidence = round(max(0.15, 0.85 - i * 0.15), 2)

            # 95% 置信区间
            ci_half = kronos_std[i] * 1.96
            close_low = round(max(limit_down, pred_close - ci_half), 2)
            close_high = round(min(limit_up, pred_close + ci_half), 2)

            pred_open = prev_close
            body_high = max(pred_open, pred_close)
            body_low = min(pred_open, pred_close)
            shadow_wick_pct = float(np.clip(wick_pct, 0.001, limit_pct * 0.2))
            pred_high = min(limit_up, body_high * (1 + shadow_wick_pct))
            pred_low = max(limit_down, body_low * (1 - shadow_wick_pct))
            prev_close = pred_close

            predictions.append({
                "day": i + 1,
                "date": dt.strftime("%Y-%m-%d"),
                "open": round(pred_open, 2),
                "high": round(pred_high, 2),
                "low": round(pred_low, 2),
                "close": round(pred_close, 2),
                "close_low": close_low,
                "close_high": close_high,
                "pct_change": pct,
                "confidence": confidence,
                "limit_pct": round(limit_pct * 100, 1),
                "limit_hit": abs(raw_close - pred_close) > 1e-6,
            })

        # ── 技术指标 ──
        tech_summary = None
        if include_technical and len(kline_data) >= 20:
            try:
                indicators = calc_all_indicators(df)
                tech_summary = {
                    "indicators": indicators,
                    "summary": summarize_indicators(indicators),
                }
            except Exception as e:
                logger.warning(f"技术指标计算失败: {e}")

        # ── 回测（新模块） ──
        backtest = None
        if backtest_windows > 0:
            try:
                bt_data = sorted(kline_data, key=lambda x: str(x.get("date", "")))
                backtest = run_backtest(
                    kline_data=bt_data,
                    predictor=self,
                    train_window=40,
                    pred_days=pred_days,
                    step=5,
                    min_windows=backtest_windows,
                )
            except Exception as e:
                logger.warning(f"回测失败: {e}")
                backtest = {"error": str(e)}

        return {
            "current_price": round(current_close, 2),
            "predictions": predictions,
            "backtest": backtest,
            "technical_summary": tech_summary,
            "market_context": {
                "beta": market_ctx["beta"],
                "index_trend_5d": market_ctx["index_trend_5d"],
                "index_trend_20d": market_ctx["index_trend_20d"],
                "market_factor": market_ctx["market_factor"],
                "market_label": market_ctx["label"],
            },
            "model": "Kronos-small (3-model blended, true MC)",
            "p1_meta": {
                "volatility_label": vol_label,
                "market_label": market_ctx["label"],
                "vote_result": vote_label,
                "limit_label": f"{limit_pct * 100:.0f}%",
            },
            "history_days": len(kline_data),
            "pred_days": pred_days,
            "disclaimer": "AI推演仅供参考，不构成投资建议",
        }


_predictor: KronosStockPredictor | None = None


def get_kronos_predictor() -> KronosStockPredictor:
    global _predictor
    if _predictor is None:
        _predictor = KronosStockPredictor()
    return _predictor
