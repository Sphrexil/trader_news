"""东方财富数据源 — 覆盖面最广的财经新闻和快讯。"""

import logging

from datasources.base import BaseDataSource, DataSourceError

logger = logging.getLogger(__name__)


class EastMoneySource(BaseDataSource):
    """东方财富新闻快讯。

    免费 API，数据量大（200条/次），覆盖政策/行业/个股/公告。
    """

    name = "eastmoney"
    priority = 1

    def is_available(self) -> bool:
        try:
            import akshare as ak
            return True
        except ImportError:
            return False

    def fetch_news(self) -> list[dict]:
        """获取东方财富全球财经快讯。"""
        try:
            import akshare as ak

            # stock_info_global_em: 东方财富全球快讯（200条）
            df = ak.stock_info_global_em()
            if df.empty:
                raise DataSourceError("EastMoney returned empty")

            cols = list(df.columns)
            items = []
            for _, row in df.iterrows():
                vals = [row[c] for c in cols]
                title = str(vals[0]) if vals[0] else ""
                content = str(vals[1]) if vals[1] and len(vals) > 1 else ""
                pub_time = str(vals[2]) if vals[2] and len(vals) > 2 else ""

                if len(title) < 10:
                    continue

                items.append({
                    "title": title[:300],
                    "content": content[:500],
                    "pub_time": pub_time,
                    "url": "",
                    "source": "东方财富",
                })
            return items
        except ImportError:
            raise DataSourceError("akshare not installed")
        except DataSourceError:
            raise
        except Exception as e:
            raise DataSourceError(f"EastMoney failed: {e}") from e
