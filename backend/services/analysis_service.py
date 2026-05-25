"""财务分析 & 公告分类服务。

- 财务分析：识别暴雷风险、判断财报是否超预期/低于预期
- 公告分类：重大违法、股东减持、重大利好
"""

import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from models.financial import Financial
from models.announcement import Announcement

logger = logging.getLogger(__name__)


# ── 公告关键词库 ─────────────────────────────────────

VIOLATION_KEYWORDS = [
    "违法", "违规", "处罚", "立案", "调查", "警示函", "监管函",
    "通报批评", "责令改正", "纪律处分", "行政处罚", "证监会",
    "内幕交易", "操纵市场", "信息披露违规", "财务造假",
]

INSIDER_SELL_KEYWORDS = [
    "减持", "股东减持", "董监高减持", "控股股东减持",
    "大宗交易", "协议转让", "集中竞价减持",
]

POSITIVE_KEYWORDS = [
    "中标", "签约", "合同", "订单", "增持", "回购",
    "业绩预增", "净利润增长", "扭亏为盈", "分红",
    "送转", "派息", "重大资产重组", "收购", "并购",
    "战略合作", "获得批文", "新产品", "新药获批",
    "专利获批", "技术突破", "产能扩大",
]


# ── 公告分类 ─────────────────────────────────────────

def classify_announcement(title: str) -> dict[str, Any]:
    """根据标题关键词对公告进行分类。

    Returns:
        {
            "title": str,
            "tags": list[str],       # 分类标签
            "has_violation": bool,   # 是否有违规风险
            "has_insider_sell": bool, # 是否有股东减持
            "has_positive": bool,    # 是否有重大利好
            "summary": str,          # 一句话总结
        }
    """
    tags = []
    violation_hits = []
    insider_hits = []
    positive_hits = []

    for kw in VIOLATION_KEYWORDS:
        if kw in title:
            violation_hits.append(kw)

    for kw in INSIDER_SELL_KEYWORDS:
        if kw in title:
            insider_hits.append(kw)

    for kw in POSITIVE_KEYWORDS:
        if kw in title:
            positive_hits.append(kw)

    if violation_hits:
        tags.append("重大违法")
    if insider_hits:
        tags.append("股东减持")
    if positive_hits:
        tags.append("重大利好")

    # 生成摘要
    parts = []
    if violation_hits:
        parts.append(f"涉及: {', '.join(violation_hits[:3])}")
    if insider_hits:
        parts.append(f"减持相关: {', '.join(insider_hits[:3])}")
    if positive_hits:
        parts.append(f"利好: {', '.join(positive_hits[:3])}")

    return {
        "title": title,
        "tags": tags,
        "has_violation": len(violation_hits) > 0,
        "has_insider_sell": len(insider_hits) > 0,
        "has_positive": len(positive_hits) > 0,
        "summary": "; ".join(parts) if parts else "其他公告",
    }


# ── 财务分析 ─────────────────────────────────────────

def analyze_financials(items: list[dict]) -> dict[str, Any]:
    """分析财务数据，生成风险评估和预期判断。

    Args:
        items: 按时间排序的财务数据列表 (最近的在前面)

    Returns:
        {
            "items": [...],
            "risk_flags": list[str],      # 风险标记
            "earnings_verdict": str,      # "超预期" / "符合预期" / "低于预期" / "数据不足"
            "latest_summary": str,        # 最新一期财报一句话总结
        }
    """
    if not items or len(items) < 1:
        return {
            "items": items or [],
            "risk_flags": [],
            "earnings_verdict": "数据不足",
            "latest_summary": "暂无财务数据",
        }

    risk_flags = []
    latest = items[0]

    # --- 暴雷风险检测 ---
    # 1. 净利润连续2个季度为负
    negative_count = 0
    for item in items:
        np_ = item.get("net_profit")
        if np_ is not None and np_ < 0:
            negative_count += 1
            if negative_count >= 2:
                risk_flags.append(f"连续{negative_count}个季度净利润为负")
                break
        else:
            break

    # 2. 净利润同比增长率连续为负且恶化
    yoy_values = [item.get("net_profit_yoy") for item in items[:4] if item.get("net_profit_yoy") is not None]
    if len(yoy_values) >= 2 and all(y < 0 for y in yoy_values):
        if len(yoy_values) >= 3 and yoy_values[0] < yoy_values[1]:
            risk_flags.append(f"净利润同比持续恶化 ({', '.join(f'{y:.1f}%' for y in yoy_values[:3])})")
        else:
            risk_flags.append("净利润连续同比下降")

    # 3. 营收连续下降
    rev_yoy = [item.get("revenue_yoy") for item in items[:3] if item.get("revenue_yoy") is not None]
    if len(rev_yoy) >= 2 and all(r < 0 for r in rev_yoy):
        risk_flags.append("营收连续同比下降")

    # --- 预期判断 ---
    earning_verdict = "数据不足"
    latest_yoy = latest.get("net_profit_yoy")
    if latest_yoy is not None:
        if latest_yoy > 20:
            earning_verdict = "超预期 (利润大增)"
        elif latest_yoy > 5:
            earning_verdict = "略超预期"
        elif latest_yoy >= -5:
            earning_verdict = "符合预期"
        elif latest_yoy >= -20:
            earning_verdict = "略低于预期"
        else:
            earning_verdict = "低于预期 (利润大减)"

    # 检查扣非净利润趋势
    if len(items) >= 2:
        deduct_yoy = latest.get("deducted_yoy")
        if deduct_yoy is not None and latest_yoy is not None:
            if deduct_yoy < latest_yoy - 10:
                risk_flags.append("扣非净利润增速远低于净利润增速（非经常性损益占比较高）")

    # --- 一句话总结 ---
    parts = []
    period = latest.get("period", "")
    if latest.get("net_profit") is not None:
        parts.append(f"净利润{_fmt_num(latest['net_profit'])}")
    if latest_yoy is not None:
        parts.append(f"同比{latest_yoy:+.1f}%")
    if latest.get("revenue") is not None:
        parts.append(f"营收{_fmt_num(latest['revenue'])}")
    if latest.get("eps") is not None:
        parts.append(f"EPS {latest['eps']:.4f}")

    return {
        "items": items,
        "risk_flags": risk_flags,
        "earnings_verdict": earning_verdict,
        "latest_summary": f"{period}: {'; '.join(parts)}" if parts else "无数据",
    }


def _fmt_num(n: float) -> str:
    if abs(n) >= 1e8:
        return f"{n/1e8:.1f}亿"
    if abs(n) >= 1e4:
        return f"{n/1e4:.1f}万"
    return f"{n:.1f}"
