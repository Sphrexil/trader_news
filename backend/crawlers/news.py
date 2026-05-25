"""财经新闻采集器 — 使用轮动数据源（新浪 → 同花顺 → AKShare）。"""

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from crawlers.base import BaseCrawler
from datasources.manager import get_ds_manager
from models.news import News

logger = logging.getLogger(__name__)


class NewsCrawler(BaseCrawler):
    """采集增量财经新闻。

    使用轮动数据源：Sina → THS → AKShare。
    每条新闻按 URL 去重，新增的写入数据库。
    """

    model = News
    index_elements = ["url"]

    def fetch(self, db: Session) -> list[dict]:
        """从轮动数据源拉取新闻。"""
        ds = get_ds_manager()
        raw_news = ds.get_news()
        if not raw_news:
            logger.warning("所有新闻数据源均失败")
            return []

        # 转换时间戳为 datetime
        records = []
        for n in raw_news:
            pub_time = n.get("pub_time", "")
            dt = None
            try:
                # Unix timestamp → datetime
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
                "sentiment": None,
            })

        logger.info("NewsCrawler: 获取到 %d 条新闻", len(records))
        return records
