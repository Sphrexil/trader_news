"""日行情模型。"""

from datetime import date

from sqlalchemy import Date, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class DailyPrice(Base):
    __tablename__ = "daily_prices"

    ts_code: Mapped[str] = mapped_column(String(12), primary_key=True, comment="股票代码")
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True, comment="交易日期")
    open: Mapped[float | None] = mapped_column(Numeric(10, 3))
    high: Mapped[float | None] = mapped_column(Numeric(10, 3))
    low: Mapped[float | None] = mapped_column(Numeric(10, 3))
    close: Mapped[float | None] = mapped_column(Numeric(10, 3))
    pre_close: Mapped[float | None] = mapped_column(Numeric(10, 3))
    pct_chg: Mapped[float | None] = mapped_column(Numeric(8, 4), comment="涨跌幅 %")
    vol: Mapped[float | None] = mapped_column(Numeric(20, 2), comment="成交量（手）")
    amount: Mapped[float | None] = mapped_column(Numeric(20, 2), comment="成交额（千元）")
    turnover_rate: Mapped[float | None] = mapped_column(Numeric(8, 4), comment="换手率 %")
    total_mv: Mapped[float | None] = mapped_column(Numeric(20, 2), comment="总市值（万元）")
    circ_mv: Mapped[float | None] = mapped_column(Numeric(20, 2), comment="流通市值（万元）")
    adj_factor: Mapped[float | None] = mapped_column(Numeric(12, 6), comment="复权因子")

    __table_args__ = (
        Index("idx_dp_date", "trade_date"),
    )
