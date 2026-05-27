"""Kronos 股价预测路由。"""

import time

from fastapi import APIRouter, Query

from schemas.common import ApiResponse

router = APIRouter(prefix="/stocks", tags=["predict"])


@router.get("/{ts_code}/predict", response_model=ApiResponse[dict])
def predict_stock(
    ts_code: str,
    days: int = Query(default=5, ge=1, le=10, description="预测天数 (1-10)"),
):
    """Kronos AI 预测未来股价走势。

    需要至少 30 天历史 K 线数据。
    模型首次调用时从 HuggingFace 下载（~100MB），后续缓存使用。
    """
    # 1. 获取历史 K 线
    try:
        from datasources.manager import get_ds_manager

        ds = get_ds_manager()
        rows = ds.get_daily_prices(ts_code, "2026-01-01", "2026-05-27")
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
        result = predictor.predict(rows, pred_days=days)
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
