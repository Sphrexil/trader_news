"""行情相关 Pydantic schemas。"""

from datetime import date, datetime

from pydantic import BaseModel


class Quote(BaseModel):
    """实时/最新行情快照。"""

    ts_code: str
    name: str
    price: float | None = None
    pre_close: float | None = None
    pct_chg: float | None = None
    change: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    vol: float | None = None
    amount: float | None = None
    turnover_rate: float | None = None
    total_mv: float | None = None
    circ_mv: float | None = None
    quote_time: datetime | None = None
    is_trading: bool = False


class KlineItem(BaseModel):
    """单条K线数据。"""

    date: date
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    vol: float | None = None
    amount: float | None = None
    pct_chg: float | None = None
    turnover_rate: float | None = None
    total_mv: float | None = None


class KlineData(BaseModel):
    """K线数据集合。"""

    ts_code: str
    period: str
    adjust: str
    items: list[KlineItem]
    count: int


class IndexItem(BaseModel):
    """指数行情。"""

    code: str
    name: str
    price: float | None = None
    pct_chg: float | None = None
    change: float | None = None
    vol: float | None = None


class MarketStats(BaseModel):
    """市场统计。"""

    up_count: int = 0
    down_count: int = 0
    flat_count: int = 0
    limit_up: int = 0
    limit_down: int = 0
    total_amount: float | None = None


class MarketOverview(BaseModel):
    indices: list[IndexItem]
    market_stats: MarketStats
    updated_at: datetime | None = None


class LeadStock(BaseModel):
    ts_code: str | None = None
    name: str
    pct_chg: float | None = None


class SectorItem(BaseModel):
    name: str
    pct_chg: float | None = None
    change_amount: float | None = None
    up_count: int = 0
    down_count: int = 0
    lead_stock: LeadStock | None = None


class SectorData(BaseModel):
    type: str
    items: list[SectorItem]
    updated_at: datetime | None = None
