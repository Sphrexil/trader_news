"""自选股与告警规则模型。"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Watchlist(Base):
    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(12), nullable=False, comment="股票代码")
    group_name: Mapped[str] = mapped_column(String(50), default="默认")
    note: Mapped[str | None] = mapped_column(Text)
    cost_price: Mapped[float | None] = mapped_column(Numeric(10, 3), comment="成本价")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("ts_code", "group_name", name="uq_watchlist_code_group"),
    )


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(12), nullable=False, comment="股票代码")
    rule_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="price_abs / price_pct / volume_ratio / ann_publish",
    )
    threshold: Mapped[float] = mapped_column(Numeric(15, 4), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False, comment="above / below")
    channel: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="bark / email / webhook",
    )
    channel_cfg: Mapped[dict] = mapped_column(JSON, nullable=False, comment="推送配置")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_triggered: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
