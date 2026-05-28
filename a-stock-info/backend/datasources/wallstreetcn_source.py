"""华尔街见闻数据源 — A 股快讯，实时性高。"""

import logging
import re

import requests

from datasources.base import BaseDataSource, DataSourceError

logger = logging.getLogger(__name__)


class WallStreetCNSource(BaseDataSource):
    """华尔街见闻 7x24 快讯。

    免费 API，无需 Token。A 股相关度高（涨停/跌停/板块/政策）。
    """

    name = "wallstreetcn"
    priority = 2

    API_URL = "https://api-one.wallstcn.com/apiv1/content/lives"
    HEADERS = {"User-Agent": "Mozilla/5.0"}

    def is_available(self) -> bool:
        try:
            r = requests.get(f"{self.API_URL}?channel=global-channel&limit=1",
                             headers=self.HEADERS, timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def fetch_news(self) -> list[dict]:
        """获取华尔街见闻快讯。"""
        try:
            r = requests.get(
                f"{self.API_URL}?channel=global-channel&limit=30",
                headers=self.HEADERS, timeout=10,
            )
            data = r.json()
            items = data.get("data", {}).get("items", [])

            results = []
            for item in items:
                # 合并 title + content_text
                title = item.get("title", "") or ""
                content = item.get("content_text", "") or ""
                full_text = (title + " " + content).strip()

                # 提取显示时间
                display_time = item.get("display_time", "")

                results.append({
                    "title": title[:200] if title else content[:200],
                    "content": full_text,
                    "pub_time": str(display_time),
                    "url": item.get("article", {}).get("uri", "") if item.get("article") else "",
                    "source": "华尔街见闻",
                })

            return results
        except Exception as e:
            raise DataSourceError(f"WallStreetCN failed: {e}") from e
