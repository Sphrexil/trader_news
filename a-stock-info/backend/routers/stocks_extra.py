"""股票附加路由（行情、K线、财务、公告）。"""

import time

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from schemas.common import ApiResponse, PaginatedData, PaginationMeta
from schemas.data import AnnouncementItem, FinancialAnalysis, FinancialData, FinancialItem
from schemas.price import KlineData, Quote
from services.data_service import AnnouncementService, FinancialService
from services.price_service import PriceService

router = APIRouter(prefix="/stocks", tags=["stocks-extra"])


@router.get("/{ts_code}/quote", response_model=ApiResponse[Quote])
def get_quote(ts_code: str, db: Session = Depends(get_db)):
    svc = PriceService(db)
    data = svc.get_quote(ts_code)
    if data is None:
        return ApiResponse(code=1002, message=f"股票不存在: {ts_code}", ts=int(time.time() * 1000))
    return ApiResponse(data=Quote(**data), ts=int(time.time() * 1000))


@router.get("/{ts_code}/kline", response_model=ApiResponse[KlineData])
def get_kline(
    ts_code: str,
    period: str = Query(default="daily"),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    adjust: str = Query(default="qfq"),
    limit: int = Query(default=500, le=2000),
    db: Session = Depends(get_db),
):
    svc = PriceService(db)
    data = svc.get_kline(
        ts_code=ts_code, period=period,
        start_date=start_date, end_date=end_date,
        adjust=adjust, limit=limit,
    )
    if data is None:
        return ApiResponse(code=1002, message=f"股票不存在: {ts_code}", ts=int(time.time() * 1000))
    if data.get("count", 0) == 0:
        return ApiResponse(code=1003, message="K线数据获取超时，请稍后重试", ts=int(time.time() * 1000))
    return ApiResponse(data=KlineData(**data), ts=int(time.time() * 1000))


@router.get("/{ts_code}/financials", response_model=ApiResponse[FinancialData])
def get_financials(
    ts_code: str,
    report_type: str = Query(default="Q"),
    limit: int = Query(default=12),
    db: Session = Depends(get_db),
):
    """财务数据 + 分析（暴雷风险 / 超预期判断）。"""
    # 1. DB
    svc = FinancialService(db)
    data = svc.get_financials(ts_code=ts_code, report_type=report_type, limit=limit)
    items = data.get("items", []) if data else []

    # 2. DB 空 → 数据源
    if not items:
        try:
            from datasources.manager import get_ds_manager
            ds = get_ds_manager()
            symbol = ts_code.split(".")[0]
            raw = ds.get_financials(symbol)
            if raw:
                items = raw
        except Exception:
            pass

    # 3. 只保留最近6个月，最新在前
    from datetime import date, timedelta
    six_months_ago = (date.today() - timedelta(days=190)).isoformat()
    parsed = []
    for it in items:
        period = str(it.get("period", ""))
        if period >= six_months_ago:
            parsed.append({
                "period": period,
                "net_profit": it.get("net_profit"),
                "net_profit_yoy": it.get("net_profit_yoy"),
                "revenue": it.get("revenue"),
                "revenue_yoy": it.get("revenue_yoy"),
                "eps": it.get("eps"),
                "deducted_profit": it.get("deducted_profit"),
                "deducted_yoy": it.get("deducted_yoy"),
            })
    parsed.sort(key=lambda x: x["period"], reverse=True)

    # 4. 分析
    from services.analysis_service import analyze_financials
    analysis = analyze_financials(parsed)

    return ApiResponse(
        data=FinancialData(
            ts_code=ts_code,
            analysis=FinancialAnalysis(
                items=[FinancialItem(**it) for it in parsed[:limit]],
                risk_flags=analysis["risk_flags"],
                earnings_verdict=analysis["earnings_verdict"],
                latest_summary=analysis["latest_summary"],
            ),
        ),
        ts=int(time.time() * 1000),
    )


@router.get("/{ts_code}/announcements", response_model=ApiResponse[PaginatedData[AnnouncementItem]])
def get_announcements(
    ts_code: str,
    ann_type: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """公告列表 + 分类（重大违法 / 股东减持 / 重大利好）。"""
    svc = AnnouncementService(db)
    items, total = svc.search(
        ts_code=ts_code, ann_type=ann_type, start_date=start_date,
        page=page, page_size=page_size,
    )

    # DB 空 → 数据源获取
    if total == 0:
        try:
            from datasources.manager import get_ds_manager
            ds = get_ds_manager()
            symbol = ts_code.split(".")[0]
            raw = ds.get_announcements(symbol)
            if raw:
                items = []
                for r in raw:
                    items.append({
                        "id": 0, "ts_code": ts_code,
                        "title": r.get("title", ""),
                        "ann_type": None,
                        "pub_date": r.get("pub_date", ""),
                        "url": r.get("url", ""),
                    })
                total = len(items)
        except Exception:
            pass

    # 分类
    from services.analysis_service import classify_announcement
    classified = []
    for item in items:
        result = classify_announcement(item.get("title", ""))
        item["tags"] = result["tags"]
        item["classification"] = result["summary"]
        item["has_violation"] = result["has_violation"]
        item["has_insider_sell"] = result["has_insider_sell"]
        item["has_positive"] = result["has_positive"]
        classified.append(item)

    # 取最近10条（数据源可能只提供历史数据）
    classified.sort(key=lambda x: x.get("pub_date", ""), reverse=True)
    classified = classified[:10]
    total = len(classified)

    pages = (total + page_size - 1) // page_size if total > 0 else 0
    return ApiResponse(
        data=PaginatedData(
            list=[AnnouncementItem(**item) for item in classified],
            pagination=PaginationMeta(
                total=total, page=page, page_size=page_size, pages=pages,
            ),
        ),
        ts=int(time.time() * 1000),
    )
