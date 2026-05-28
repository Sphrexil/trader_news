"""行情路由。"""

import time

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from schemas.common import ApiResponse
from schemas.price import MarketOverview, SectorData
from services.price_service import PriceService

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/overview", response_model=ApiResponse[MarketOverview])
def get_market_overview(db: Session = Depends(get_db)):
    """大盘概况。"""
    svc = PriceService(db)
    data = svc.get_market_overview()
    return ApiResponse(data=MarketOverview(**data), ts=int(time.time() * 1000))


@router.get("/sectors", response_model=ApiResponse[SectorData])
def get_sectors(
    type: str = Query(default="industry", description="industry / concept"),
    db: Session = Depends(get_db),
):
    """板块涨跌幅。"""
    svc = PriceService(db)
    data = svc.get_sectors(sector_type=type)
    return ApiResponse(data=SectorData(**data), ts=int(time.time() * 1000))
