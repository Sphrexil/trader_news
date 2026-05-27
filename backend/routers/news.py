"""新闻路由。"""

import time

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from schemas.common import ApiResponse, PaginatedData, PaginationMeta
from schemas.data import NewsItem
from services.data_service import NewsService
from services.news_pipeline import classify, hot_score, relevance_score, sentiment_score

router = APIRouter(prefix="/news", tags=["news"])


@router.get("", response_model=ApiResponse[PaginatedData[NewsItem]])
def list_news(
    ts_code: str | None = Query(default=None, description="过滤关联某只股票"),
    source: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """新闻列表（含情感分析/利好利空分类/热度排序）。"""
    svc = NewsService(db)
    items, total = svc.search(ts_code=ts_code, source=source, page=page, page_size=page_size)

    # 对每条新闻运行分析管线
    enriched = []
    for item in items:
        title = item.get("title", "")
        if not item.get("sentiment"):
            item["sentiment"] = sentiment_score(title)
        cls = classify(title)
        item["sentiment_label"] = cls["label"]
        item["relevance"] = relevance_score(title)
        item["hot_score"] = hot_score(item["sentiment"] or 0, item["relevance"])
        item["positive_matches"] = cls["positive_matches"]
        item["negative_matches"] = cls["negative_matches"]
        enriched.append(item)

    # 过滤低质：相关性不足或热度为0的过滤
    # 放宽过滤，保证至少20条
    filtered = [
        it for it in enriched
        if it["relevance"] >= 0.01 or it["sentiment_label"] != "中性"
    ]
    filtered.sort(key=lambda x: x["hot_score"], reverse=True)

    total_filtered = len(filtered)
    start = (page - 1) * page_size
    paged = filtered[start : start + page_size]
    pages = (total_filtered + page_size - 1) // page_size if total_filtered > 0 else 0
    return ApiResponse(
        data=PaginatedData(
            list=[NewsItem(**it) for it in paged],
            pagination=PaginationMeta(
                total=total_filtered, page=page, page_size=page_size, pages=pages,
            ),
        ),
        ts=int(time.time() * 1000),
    )
