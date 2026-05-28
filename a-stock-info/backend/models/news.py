"""财经新闻模型。"""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class News(Base):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, comment="来源，如 东方财富")
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    pub_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    related_codes: Mapped[str | None] = mapped_column(String(200), comment="关联股票代码，逗号分隔")
    sentiment: Mapped[float | None] = mapped_column(Numeric(4, 2), comment="情感分 -1~1")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_news_time", "pub_time"),
    )
