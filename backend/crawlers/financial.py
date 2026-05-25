"""财务数据采集器。"""

import logging
import time

from sqlalchemy.orm import Session

from config import get_settings
from crawlers.base import BaseCrawler
from models.financial import Financial

logger = logging.getLogger(__name__)
settings = get_settings()


class FinancialCrawler(BaseCrawler):
    """采集最新季报/年报。"""

    model = Financial
    index_elements = ["ts_code", "period"]

    def fetch(self, db: Session) -> list[dict]:
        """从 AKShare 拉取财务数据。"""
        try:
            import akshare as ak

            from models.stock import Stock

            codes_query = db.query(Stock.ts_code).filter(Stock.delist_date.is_(None)).all()
            records = []

            for (ts_code,) in codes_query:
                symbol = ts_code.split(".")[0]
                try:
                    df = ak.stock_financial_abstract_ths(symbol=symbol, indicator="按报告期")
                    if df.empty:
                        continue

                    latest = df.iloc[-1]
                    period = str(latest.get("报告期", ""))
                    report_type = "Q" if "Q" in period else "Y"

                    records.append({
                        "ts_code": ts_code,
                        "period": period,
                        "report_type": report_type,
                        "revenue": float(latest.get("营业总收入", 0)) if latest.get("营业总收入") else None,
                        "net_profit": float(latest.get("归母净利润", 0)) if latest.get("归母净利润") else None,
                        "gross_margin": None,
                        "net_margin": None,
                        "total_assets": float(latest.get("资产总计", 0)) if latest.get("资产总计") else None,
                        "total_debt": float(latest.get("负债合计", 0)) if latest.get("负债合计") else None,
                        "equity": float(latest.get("股东权益", 0)) if latest.get("股东权益") else None,
                        "debt_ratio": None,
                        "cfo": None,
                        "roe": float(latest.get("净资产收益率", 0)) if latest.get("净资产收益率") else None,
                        "eps": float(latest.get("每股收益", 0)) if latest.get("每股收益") else None,
                        "bvps": float(latest.get("每股净资产", 0)) if latest.get("每股净资产") else None,
                    })
                    time.sleep(settings.CRAWLER_POLITE_DELAY)
                except Exception as e:
                    logger.debug("获取 %s 财务数据失败: %s", ts_code, e)
                    continue

            logger.info("FinancialCrawler: 获取到 %d 条财务数据", len(records))
            return records
        except ImportError:
            logger.warning("akshare 未安装，跳过财务采集")
            return []
