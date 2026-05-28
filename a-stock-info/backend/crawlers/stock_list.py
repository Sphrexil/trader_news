"""股票列表采集器（全量元数据同步）。"""

import logging
import time

from sqlalchemy.orm import Session

from config import get_settings
from crawlers.base import BaseCrawler
from models.stock import Stock

logger = logging.getLogger(__name__)
settings = get_settings()


class StockListCrawler(BaseCrawler):
    """同步全量 A 股股票列表。"""

    model = Stock
    index_elements = ["ts_code"]
    update_cols = ["name", "market", "industry", "list_date", "total_share", "float_share"]

    def fetch(self, db: Session) -> list[dict]:
        """从 AKShare 拉取股票列表。"""
        try:
            import akshare as ak

            df = ak.stock_info_a_code_name()
            records = []
            for _, row in df.iterrows():
                ts_code = str(row.get("code", ""))
                if not ts_code:
                    continue

                # 根据代码前缀判断市场
                code_num = ts_code
                if code_num.startswith("6"):
                    market = "SH"
                    ts_code = f"{code_num}.SH"
                elif code_num.startswith("0") or code_num.startswith("3"):
                    market = "SZ"
                    ts_code = f"{code_num}.SZ"
                elif code_num.startswith("8") or code_num.startswith("4"):
                    market = "BJ"
                    ts_code = f"{code_num}.BJ"
                else:
                    continue

                records.append({
                    "ts_code": ts_code,
                    "name": str(row.get("name", "")),
                    "market": market,
                    "industry": str(row.get("industry", "")) if row.get("industry") else None,
                    "list_date": None,
                    "total_share": None,
                    "float_share": None,
                })
                time.sleep(settings.CRAWLER_POLITE_DELAY)

            logger.info("StockListCrawler: 获取到 %d 只股票", len(records))
            return records
        except ImportError:
            logger.warning("akshare 未安装，跳过股票列表采集")
            return []
