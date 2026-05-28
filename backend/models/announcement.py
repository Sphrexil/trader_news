"""公告模型。"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_code: Mapped[str] = mapped_column(String(12), nullable=False, comment="股票代码")
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    ann_type: Mapped[str | None] = mapped_column(String(50), comment="公告类型")
    pub_date: Mapped[date] = mapped_column(Date, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    summary: Mapped[str | None] = mapped_column(Text, comment="NLP摘要")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_ann_code_date", "ts_code", "pub_date"),
    )
