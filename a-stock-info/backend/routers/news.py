"""新闻路由。"""

import time

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from schemas.common import ApiResponse, PaginatedData, PaginationMeta
from schemas.data import NewsItem
from services.data_service import NewsService
from services.news_pipeline import (
    analyze_impact, classify, generate_summary, hot_score, is_breaking_news,
    relevance_score, sentiment_score,
)

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
        item["hot_score"] = hot_score(item["sentiment"] or 0, item["relevance"], item.get("pub_time", ""))
        item["positive_matches"] = cls["positive_matches"]
        item["negative_matches"] = cls["negative_matches"]
        enriched.append(item)

    # 按热度排序，不做硬过滤（采集管线已做质量筛选）
    enriched.sort(key=lambda x: x["hot_score"], reverse=True)

    total_items = total  # 使用 DB 真实总数，而非当前页截断数
    start = (page - 1) * page_size
    # DB 查询已分页，无需再切片
    pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
    for it in enriched:
        impact = analyze_impact(it.get("title", ""), "", it.get("sentiment") or 0)
        it.setdefault("summary", generate_summary(it.get("title", "")))
        it.setdefault("impact_sectors", impact["impact_sectors"])
        it.setdefault("impact_level", impact["impact_level"])
        it.setdefault("investment_note", impact["investment_note"])
        it.setdefault("is_breaking", is_breaking_news(
            it.get("title", ""), it.get("sentiment") or 0, it.get("relevance", 0),
        ))

    return ApiResponse(
        data=PaginatedData(
            list=[NewsItem(**it) for it in enriched],
            pagination=PaginationMeta(
                total=total_items, page=page, page_size=page_size, pages=pages,
            ),
        ),
        ts=int(time.time() * 1000),
    )
