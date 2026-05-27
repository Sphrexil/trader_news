"""告警规则路由。"""

import logging
import time
from datetime import datetime

import pytz
import requests
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
logger = logging.getLogger(__name__)


def _send_push(rule: dict) -> tuple[bool, str]:
    """发送推送通知。支持 Bark / Email / Webhook。"""
    channel = rule.get("channel", "bark")
    cfg = rule.get("channel_cfg", {})

    if channel == "bark":
        bark_key = cfg.get("bark_key", "") or cfg.get("key", "")
        if not bark_key:
            return False, "Bark key 未配置"
        try:
            title = f"告警: {rule.get('stock_name', rule.get('ts_code', ''))}"
            body = (
                f"规则: {rule.get('rule_type')} {rule.get('direction')} {rule.get('threshold')}\n"
                f"股票: {rule.get('ts_code')}"
            )
            url = f"https://api.day.app/{bark_key}/{title}/{body}"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                return True, "Bark推送发送成功"
            return False, f"Bark返回 {r.status_code}"
        except Exception as e:
            return False, f"Bark推送失败: {e}"

    elif channel == "email":
        return False, "Email 推送暂未实现（需配置 SMTP）"

    elif channel == "webhook":
        webhook_url = cfg.get("url", "")
        if not webhook_url:
            return False, "Webhook URL 未配置"
        try:
            payload = {
                "title": f"告警: {rule.get('ts_code')}",
                "rule_type": rule.get("rule_type"),
                "threshold": rule.get("threshold"),
                "direction": rule.get("direction"),
            }
            r = requests.post(webhook_url, json=payload, timeout=10)
            return r.status_code < 400, f"Webhook返回 {r.status_code}"
        except Exception as e:
            return False, f"Webhook推送失败: {e}"

    return False, f"不支持的推送渠道: {channel}"


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

    # 实际推送
    success, msg = _send_push(rule)
    return ApiResponse(
        data=AlertTestResult(
            success=success,
            message=msg,
            sent_at=datetime.now(CN_TZ),
        ),
        ts=int(time.time() * 1000),
    )
