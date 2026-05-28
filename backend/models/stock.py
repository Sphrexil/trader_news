"""股票基础信息模型。"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Stock(Base):
    __tablename__ = "stocks"

    ts_code: Mapped[str] = mapped_column(String(12), primary_key=True, comment="股票代码，如 600000.SH")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="股票名称")
    market: Mapped[str] = mapped_column(String(10), nullable=False, comment="市场 SH/SZ/BJ")
    industry: Mapped[str | None] = mapped_column(String(50), comment="申万一级行业")
    list_date: Mapped[date | None] = mapped_column(Date, comment="上市日期")
    delist_date: Mapped[date | None] = mapped_column(Date, comment="退市日期，NULL=在市")
    total_share: Mapped[float | None] = mapped_column(Numeric(20, 2), comment="总股本（万股）")
    float_share: Mapped[float | None] = mapped_column(Numeric(20, 2), comment="流通股本（万股）")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
