"""自选股路由。"""

import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas.common import ApiResponse
from schemas.data import WatchlistCreate, WatchlistCreated, WatchlistData, WatchlistUpdate
from services.data_service import WatchlistService

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=ApiResponse[WatchlistData])
def get_watchlist(db: Session = Depends(get_db)):
    """获取自选股列表（含实时行情）。"""
    svc = WatchlistService(db)
    data = svc.get_all()
    return ApiResponse(data=WatchlistData(**data), ts=int(time.time() * 1000))


@router.post("", response_model=ApiResponse[WatchlistCreated], status_code=201)
def add_watchlist(body: WatchlistCreate, db: Session = Depends(get_db)):
    """添加自选股。"""
    svc = WatchlistService(db)
    result = svc.add(
        ts_code=body.ts_code,
        group_name=body.group_name,
        note=body.note,
        cost_price=body.cost_price,
    )
    return ApiResponse(data=WatchlistCreated(**result), ts=int(time.time() * 1000))


@router.put("/{item_id}", response_model=ApiResponse[WatchlistCreated])
def update_watchlist(item_id: int, body: WatchlistUpdate, db: Session = Depends(get_db)):
    """修改自选股。"""
    svc = WatchlistService(db)
    result = svc.update(item_id, body.model_dump(exclude_none=True))
    if result is None:
        return ApiResponse(code=1002, message=f"自选股不存在: {item_id}", ts=int(time.time() * 1000))
    return ApiResponse(data=WatchlistCreated(**result), ts=int(time.time() * 1000))


@router.delete("/{item_id}", response_model=ApiResponse[dict])
def delete_watchlist(item_id: int, db: Session = Depends(get_db)):
    """删除自选股。"""
    svc = WatchlistService(db)
    ok = svc.delete(item_id)
    if not ok:
        return ApiResponse(code=1002, message=f"自选股不存在: {item_id}", ts=int(time.time() * 1000))
    return ApiResponse(data={"deleted_id": item_id}, ts=int(time.time() * 1000))
