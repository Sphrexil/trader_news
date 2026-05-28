"""Kronos 股价预测路由。v2.2 增强版。"""

import time
from datetime import date as dt_date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models.stock import Stock
from schemas.common import ApiResponse

router = APIRouter(prefix="/stocks", tags=["predict"])


@router.get("/{ts_code}/predict", response_model=ApiResponse[dict])
def predict_stock(
    ts_code: str,
    days: int = Query(default=5, ge=1, le=10, description="预测天数 (1-10)"),
    include_technical: bool = Query(default=True, description="是否返回技术指标"),
    backtest_windows: int = Query(default=0, ge=0, le=20, description="回测窗口数 (0=不回测)"),
    db: Session = Depends(get_db),
):
    """Kronos AI 预测未来股价走势 (v2.2 增强版)。

    改进：
    - 真正的蒙特卡洛采样，每次结果不同
    - 基于采样离散度的置信区间
    - Beta 动态大盘联动
    - 独立回测模块 + 随机游走基线对比
    - 技术指标辅助参考

    需要至少 30 天历史 K 线数据。
    模型首次调用时从 HuggingFace 下载 (~100MB)，后续缓存使用。
    """
    stock = db.query(Stock).filter(Stock.ts_code == ts_code).first()

    # 1. 获取历史 K 线 + 附加今日实时行情
    try:
        from datasources.manager import get_ds_manager

        ds = get_ds_manager()
        today_str = dt_date.today().isoformat()
        rows = ds.get_daily_prices(ts_code, "2026-01-01", today_str)

        # 确保每条数据带 ts_code
        for r in rows:
            if "ts_code" not in r:
                r["ts_code"] = ts_code

        # 附加今日实时行情到 K 线末尾
        last_date = rows[-1].get("date", "")[:10] if rows else ""
        if last_date != today_str:
            try:
                q = ds.get_stock_quote(ts_code)
                if q and q.price:
                    rows.append({
                        "ts_code": ts_code,
                        "date": today_str,
                        "open": q.open if q.open else q.price,
                        "high": q.high if q.high else q.price,
                        "low": q.low if q.low else q.price,
                        "close": q.price,
                        "volume": q.vol,
                        "amount": q.amount,
                    })
            except Exception:
                pass

        if not rows or len(rows) < 30:
            return ApiResponse(
                code=1003,
                message=f"历史K线数据不足 ({len(rows) if rows else 0} 条, 至少30条)",
                ts=int(time.time() * 1000),
            )
    except Exception as e:
        return ApiResponse(
            code=1003,
            message=f"获取K线数据失败: {e}",
            ts=int(time.time() * 1000),
        )

    # 2. Kronos 预测
    try:
        from predictors.kronos_predictor import get_kronos_predictor

        predictor = get_kronos_predictor()
        result = predictor.predict(
            rows,
            pred_days=days,
            include_technical=include_technical,
            backtest_windows=backtest_windows,
            ts_code=ts_code,
            stock_name=stock.name if stock else None,
        )
    except Exception as e:
        return ApiResponse(
            code=5001,
            message=f"预测失败: {e}",
            ts=int(time.time() * 1000),
        )

    if "error" in result:
        return ApiResponse(
            code=1003,
            message=result["error"],
            ts=int(time.time() * 1000),
        )

    return ApiResponse(
        data={
            "ts_code": ts_code,
            **result,
        },
        ts=int(time.time() * 1000),
    )
