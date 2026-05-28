"""股票相关 Pydantic schemas。"""

from datetime import date

from pydantic import BaseModel


class StockBrief(BaseModel):
    """搜索列表中的股票摘要。"""

    ts_code: str
    name: str
    market: str
    industry: str | None = None
    list_date: date | None = None
    total_mv: float | None = None
    circ_mv: float | None = None
    pct_chg: float | None = None

    model_config = {"from_attributes": True}


class StockInfo(BaseModel):
    """个股基础信息（详情页）。"""

    ts_code: str
    name: str
    market: str
    industry: str | None = None
    list_date: date | None = None
    total_share: float | None = None
    float_share: float | None = None
    is_listed: bool = True

    model_config = {"from_attributes": True}
