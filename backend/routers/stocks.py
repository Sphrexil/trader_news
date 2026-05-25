"""股票基础信息路由。"""

import time

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from schemas.common import ApiResponse, PaginatedData, PaginationMeta
from schemas.stock import StockBrief, StockInfo
from services.stock_service import StockService

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("", response_model=ApiResponse[PaginatedData[StockBrief]])
def list_stocks(
    q: str | None = Query(default=None, description="模糊搜索代码/名称"),
    market: str | None = Query(default=None, description="SH / SZ / BJ"),
    industry: str | None = Query(default=None, description="申万一级行业"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """搜索/列表股票。"""
    svc = StockService(db)
    items, total = svc.search(q=q, market=market, industry=industry, page=page, page_size=page_size)
    pages = (total + page_size - 1) // page_size if total > 0 else 0
    return ApiResponse(
        data=PaginatedData(
            list=[StockBrief(**item) for item in items],
            pagination=PaginationMeta(
                total=total, page=page, page_size=page_size, pages=pages,
            ),
        ),
        ts=int(time.time() * 1000),
    )


@router.get("/{ts_code}", response_model=ApiResponse[StockInfo])
def get_stock(ts_code: str, db: Session = Depends(get_db)):
    """获取个股基础信息。"""
    svc = StockService(db)
    info = svc.get_info(ts_code)
    if info is None:
        return ApiResponse(code=1002, message=f"股票不存在: {ts_code}", ts=int(time.time() * 1000))
    return ApiResponse(data=StockInfo(**info), ts=int(time.time() * 1000))
