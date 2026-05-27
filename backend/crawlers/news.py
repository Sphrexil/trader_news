"""财经新闻采集器 — 轮动数据源 + 智能管线。"""

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from crawlers.base import BaseCrawler
from datasources.manager import get_ds_manager
from models.news import News
from services.news_pipeline import process

logger = logging.getLogger(__name__)


class NewsCrawler(BaseCrawler):
    """采集增量财经新闻。

    流程: 轮动数据源 → 去重 → 情感打分 → 相关性过滤 → 热度排序 → 写入DB
    """

    model = News
    index_elements = ["url"]

    def fetch(self, db: Session) -> list[dict]:
        """从轮动数据源拉取新闻，经管线处理。"""
        ds = get_ds_manager()
        raw_news = ds.get_news()
        if not raw_news:
            logger.warning("所有新闻数据源均失败")
            return []

        # 智能管线处理
        processed = process(raw_news, top_n=30)
        logger.info("管线处理: %d → %d 条", len(raw_news), len(processed))

        records = []
        for n in processed:
            pub_time = n.get("pub_time", "")
            dt = None
            try:
                ts = int(pub_time)
                if ts > 1000000000:
                    dt = datetime.fromtimestamp(ts)
                else:
                    dt = datetime.now()
            except (ValueError, TypeError):
                dt = datetime.now()

            records.append({
                "source": n.get("source", "未知"),
                "title": n.get("title", ""),
                "url": n.get("url", ""),
                "pub_time": dt.isoformat() if dt else datetime.now().isoformat(),
                "related_codes": n.get("related_codes"),
                "sentiment": n.get("sentiment"),
            })

        return records
