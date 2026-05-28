"""新闻路由。"""

import time

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from schemas.common import ApiResponse, PaginatedData, PaginationMeta
from schemas.data import NewsItem
from services.data_service import NewsService

router = APIRouter(prefix="/news", tags=["news"])


@router.get("", response_model=ApiResponse[PaginatedData[NewsItem]])
def list_news(
    ts_code: str | None = Query(default=None, description="过滤关联某只股票"),
    source: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """新闻列表。"""
    svc = NewsService(db)
    items, total = svc.search(ts_code=ts_code, source=source, page=page, page_size=page_size)
    pages = (total + page_size - 1) // page_size if total > 0 else 0
    return ApiResponse(
        data=PaginatedData(
            list=[NewsItem(**item) for item in items],
            pagination=PaginationMeta(
                total=total, page=page, page_size=page_size, pages=pages,
            ),
        ),
        ts=int(time.time() * 1000),
    )
