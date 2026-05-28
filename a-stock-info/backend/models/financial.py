"""财务数据模型。"""

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Financial(Base):
    __tablename__ = "financials"

    ts_code: Mapped[str] = mapped_column(String(12), primary_key=True, comment="股票代码")
    period: Mapped[str] = mapped_column(String(10), primary_key=True, comment="报告期，如 2024Q1")
    report_type: Mapped[str] = mapped_column(String(10), nullable=False, comment="Q 季报 / Y 年报")
    # 利润表
    revenue: Mapped[float | None] = mapped_column(Numeric(20, 2), comment="营业收入")
    net_profit: Mapped[float | None] = mapped_column(Numeric(20, 2), comment="归母净利润")
    gross_margin: Mapped[float | None] = mapped_column(Numeric(8, 4), comment="毛利率 %")
    net_margin: Mapped[float | None] = mapped_column(Numeric(8, 4), comment="净利率 %")
    # 资产负债表
    total_assets: Mapped[float | None] = mapped_column(Numeric(20, 2))
    total_debt: Mapped[float | None] = mapped_column(Numeric(20, 2))
    equity: Mapped[float | None] = mapped_column(Numeric(20, 2))
    debt_ratio: Mapped[float | None] = mapped_column(Numeric(8, 4), comment="资产负债率 %")
    # 现金流
    cfo: Mapped[float | None] = mapped_column(Numeric(20, 2), comment="经营活动现金流净额")
    # KPI
    roe: Mapped[float | None] = mapped_column(Numeric(8, 4), comment="净资产收益率 %")
    eps: Mapped[float | None] = mapped_column(Numeric(10, 4), comment="每股收益")
    bvps: Mapped[float | None] = mapped_column(Numeric(10, 4), comment="每股净资产")
