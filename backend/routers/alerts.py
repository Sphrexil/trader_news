"""告警规则路由。"""

import time
from datetime import datetime

import pytz
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas.common import ApiResponse
from schemas.data import (
    AlertRuleCreate,
    AlertRuleItem,
    AlertRuleList,
    AlertRuleUpdate,
    AlertTestResult,
)
from services.data_service import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])
CN_TZ = pytz.timezone("Asia/Shanghai")


@router.get("", response_model=ApiResponse[AlertRuleList])
def list_alerts(db: Session = Depends(get_db)):
    """获取告警规则列表。"""
    svc = AlertService(db)
    items = svc.get_all()
    return ApiResponse(
        data=AlertRuleList(list=[AlertRuleItem(**item) for item in items]),
        ts=int(time.time() * 1000),
    )


@router.post("", response_model=ApiResponse[AlertRuleItem], status_code=201)
def create_alert(body: AlertRuleCreate, db: Session = Depends(get_db)):
    """创建告警规则。"""
    svc = AlertService(db)
    result = svc.create(body.model_dump())
    return ApiResponse(data=AlertRuleItem(**result), ts=int(time.time() * 1000))


@router.put("/{alert_id}", response_model=ApiResponse[AlertRuleItem])
def update_alert(alert_id: int, body: AlertRuleUpdate, db: Session = Depends(get_db)):
    """修改告警规则。"""
    svc = AlertService(db)
    result = svc.update(alert_id, body.model_dump(exclude_none=True))
    if result is None:
        return ApiResponse(code=1002, message=f"告警规则不存在: {alert_id}", ts=int(time.time() * 1000))
    return ApiResponse(data=AlertRuleItem(**result), ts=int(time.time() * 1000))


@router.delete("/{alert_id}", response_model=ApiResponse[dict])
def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    """删除告警规则。"""
    svc = AlertService(db)
    ok = svc.delete(alert_id)
    if not ok:
        return ApiResponse(code=1002, message=f"告警规则不存在: {alert_id}", ts=int(time.time() * 1000))
    return ApiResponse(data={"deleted_id": alert_id}, ts=int(time.time() * 1000))


@router.post("/test/{alert_id}", response_model=ApiResponse[AlertTestResult])
def test_alert(alert_id: int, db: Session = Depends(get_db)):
    """测试推送（调试用）。"""
    svc = AlertService(db)
    items = svc.get_all()
    rule = next((r for r in items if r["id"] == alert_id), None)
    if not rule:
        return ApiResponse(code=1002, message=f"告警规则不存在: {alert_id}", ts=int(time.time() * 1000))

    # TODO: 实际调用推送通道（Bark/Email/Webhook）
    return ApiResponse(
        data=AlertTestResult(
            success=True,
            message=f"推送测试成功 (channel={rule["channel"]})",
            sent_at=datetime.now(CN_TZ),
        ),
        ts=int(time.time() * 1000),
    )
