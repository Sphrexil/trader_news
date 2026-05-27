"""财务数据、公告、新闻、自选股、告警规则 schemas。"""

from datetime import date, datetime

from pydantic import BaseModel, Field


# ── 财务数据 ─────────────────────────────────────────

class FinancialItem(BaseModel):
    period: str
    report_type: str = "Q"
    net_profit: float | None = None
    net_profit_yoy: float | None = None
    revenue: float | None = None
    revenue_yoy: float | None = None
    eps: float | None = None
    deducted_profit: float | None = None
    deducted_yoy: float | None = None

    model_config = {"from_attributes": True}


class FinancialAnalysis(BaseModel):
    items: list[FinancialItem] = []
    risk_flags: list[str] = []
    earnings_verdict: str = "数据不足"
    latest_summary: str = ""


class FinancialData(BaseModel):
    ts_code: str
    analysis: FinancialAnalysis | None = None


# ── 公告 ─────────────────────────────────────────────

class AnnouncementItem(BaseModel):
    id: int
    ts_code: str
    title: str
    ann_type: str | None = None
    pub_date: date
    url: str
    tags: list[str] = []
    classification: str = ""
    has_violation: bool = False
    has_insider_sell: bool = False
    has_positive: bool = False

    model_config = {"from_attributes": True}


# ── 新闻 ─────────────────────────────────────────────

class NewsItem(BaseModel):
    id: int
    source: str
    title: str
    url: str
    pub_time: datetime
    related_codes: list[str] | None = None
    sentiment: float | None = None
    sentiment_label: str = "中性"
    relevance: float = 0.0
    hot_score: float = 0.0
    positive_matches: list[str] = []
    negative_matches: list[str] = []

    model_config = {"from_attributes": True}


# ── 自选股 ───────────────────────────────────────────

class WatchlistStock(BaseModel):
    id: int
    ts_code: str
    name: str
    price: float | None = None
    pct_chg: float | None = None
    change: float | None = None
    vol: float | None = None
    cost_price: float | None = None
    pnl_pct: float | None = None
    note: str | None = None
    added_at: datetime | None = None


class WatchlistGroup(BaseModel):
    group_name: str
    stocks: list[WatchlistStock]


class WatchlistData(BaseModel):
    groups: list[WatchlistGroup]


class WatchlistCreate(BaseModel):
    ts_code: str
    group_name: str = "默认"
    note: str | None = None
    cost_price: float | None = None


class WatchlistUpdate(BaseModel):
    group_name: str | None = None
    note: str | None = None
    cost_price: float | None = None


class WatchlistCreated(BaseModel):
    id: int
    ts_code: str
    group_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── 告警规则 ─────────────────────────────────────────

class AlertRuleItem(BaseModel):
    id: int
    ts_code: str
    stock_name: str | None = None
    rule_type: str
    threshold: float
    direction: str
    channel: str
    channel_cfg: dict
    is_active: bool = True
    last_triggered: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertRuleList(BaseModel):
    list: list[AlertRuleItem]


class AlertRuleCreate(BaseModel):
    ts_code: str
    rule_type: str = Field(description="price_abs / price_pct / volume_ratio / ann_publish")
    threshold: float
    direction: str = Field(default="above", description="above / below")
    channel: str = Field(default="bark")
    channel_cfg: dict


class AlertRuleUpdate(BaseModel):
    threshold: float | None = None
    is_active: bool | None = None
    direction: str | None = None
    channel_cfg: dict | None = None


class AlertTestResult(BaseModel):
    success: bool
    message: str
    sent_at: datetime | None = None
