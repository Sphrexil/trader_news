"""公告采集器。"""

import logging
import time
from datetime import date

from sqlalchemy.orm import Session

from config import get_settings
from crawlers.base import BaseCrawler
from models.announcement import Announcement
from models.stock import Stock

logger = logging.getLogger(__name__)
settings = get_settings()


class AnnouncementCrawler(BaseCrawler):
    """采集增量公告。"""

    model = Announcement
    index_elements = ["url"]

    def fetch(self, db: Session) -> list[dict]:
        """从 AKShare 拉取公告。"""
        try:
            import akshare as ak

            from models.stock import Stock

            codes_query = db.query(Stock.ts_code).filter(Stock.delist_date.is_(None)).all()
            records = []

            for (ts_code,) in codes_query:
                symbol = ts_code.split(".")[0]
                try:
                    df = ak.stock_notice_report(symbol=symbol)
                    if df.empty:
                        continue

                    # 取最近30天公告
                    for _, row in df.head(5).iterrows():
                        records.append({
                            "ts_code": ts_code,
                            "title": str(row.get("标题", "")),
                            "ann_type": str(row.get("类型", "")) if row.get("类型") else None,
                            "pub_date": date.today(),
                            "url": str(row.get("公告链接", f"notice:{ts_code}:{row.get('标题', '')}")),
                            "summary": None,
                        })
                    time.sleep(settings.CRAWLER_POLITE_DELAY)
                except Exception as e:
                    logger.debug("获取 %s 公告失败: %s", ts_code, e)
                    continue

            logger.info("AnnouncementCrawler: 获取到 %d 条公告", len(records))
            return records
        except ImportError:
            logger.warning("akshare 未安装，跳过公告采集")
            return []
