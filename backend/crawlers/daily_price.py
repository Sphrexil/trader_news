"""日行情采集器。"""

import logging
import time
from datetime import date

from sqlalchemy.orm import Session

from config import get_settings
from crawlers.base import BaseCrawler
from models.daily_price import DailyPrice
from models.stock import Stock

logger = logging.getLogger(__name__)
settings = get_settings()


class DailyPriceCrawler(BaseCrawler):
    """采集全量日行情数据。"""

    model = DailyPrice
    index_elements = ["ts_code", "trade_date"]

    def fetch(self, db: Session) -> list[dict]:
        """从 AKShare 拉取当日全量行情。"""
        try:
            import akshare as ak

            codes_query = db.query(Stock.ts_code).filter(Stock.delist_date.is_(None)).all()
            codes = [c[0] for c in codes_query]

            if not codes:
                logger.warning("股票列表为空，跳过日行情采集")
                return []

            today = date.today().isoformat()
            records = []

            for ts_code in codes:
                symbol = ts_code.split(".")[0]
                try:
                    df = ak.stock_zh_a_hist(
                        symbol=symbol,
                        period="daily",
                        start_date=today,
                        end_date=today,
                        adjust="qfq",
                    )
                    if df.empty:
                        continue

                    row = df.iloc[-1]
                    records.append({
                        "ts_code": ts_code,
                        "trade_date": today,
                        "open": float(row.get("开盘", 0)) if row.get("开盘") else None,
                        "high": float(row.get("最高", 0)) if row.get("最高") else None,
                        "low": float(row.get("最低", 0)) if row.get("最低") else None,
                        "close": float(row.get("收盘", 0)) if row.get("收盘") else None,
                        "pre_close": float(row.get("昨收", 0)) if row.get("昨收") else None,
                        "pct_chg": float(row.get("涨跌幅", 0)) if row.get("涨跌幅") else None,
                        "vol": float(row.get("成交量", 0)) if row.get("成交量") else None,
                        "amount": float(row.get("成交额", 0)) if row.get("成交额") else None,
                        "turnover_rate": float(row.get("换手率", 0)) if row.get("换手率") else None,
                    })
                    time.sleep(settings.CRAWLER_POLITE_DELAY)
                except Exception as e:
                    logger.debug("获取 %s 行情失败: %s", ts_code, e)
                    continue

            logger.info("DailyPriceCrawler: 获取到 %d 条行情", len(records))
            return records
        except ImportError:
            logger.warning("akshare 未安装，跳过日行情采集")
            return []
