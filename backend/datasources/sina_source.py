"""新浪财经数据源 — 免费、无需Token、支持指数和个股行情。"""

import logging
import re
from typing import Any

import requests

from datasources.base import (
    BaseDataSource,
    DataSourceError,
    IndexData,
    StockQuote,
)

logger = logging.getLogger(__name__)

# 新浪代码映射
SINA_INDEX_MAP = {
    "000001.SH": "s_sh000001",
    "399001.SZ": "s_sz399001",
    "399006.SZ": "s_sz399006",
    "899050.BJ": "s_bj899050",
}

INDEX_NAMES = {
    "000001.SH": "上证指数",
    "399001.SZ": "深证成指",
    "399006.SZ": "创业板指",
    "899050.BJ": "北证50",
}


class SinaDataSource(BaseDataSource):
    """新浪财经 HTTP 接口。

    免费、无需 API Token、支持指数 + 个股实时行情。
    数据格式: var hq_str_<code>="字段1,字段2,..."
    """

    name = "sina"
    priority = 1

    BASE_URL = "http://hq.sinajs.cn/list="
    HEADERS = {"Referer": "https://finance.sina.com.cn"}

    def is_available(self) -> bool:
        try:
            r = requests.get(self.BASE_URL + "s_sh000001", headers=self.HEADERS, timeout=5)
            return r.status_code == 200 and "hq_str" in r.text
        except Exception:
            return False

    def fetch_indices(self, codes: list[str]) -> list[IndexData]:
        sina_codes = []
        for c in codes:
            sc = SINA_INDEX_MAP.get(c)
            if sc:
                sina_codes.append(sc)

        if not sina_codes:
            return []

        url = self.BASE_URL + ",".join(sina_codes)
        try:
            r = requests.get(url, headers=self.HEADERS, timeout=10)
            if r.status_code != 200:
                raise DataSourceError(f"Sina HTTP {r.status_code}")
        except requests.RequestException as e:
            raise DataSourceError(f"Sina unavailable: {e}") from e

        results = []
        for c in codes:
            sc = SINA_INDEX_MAP.get(c)
            if not sc:
                continue
            data = self._parse_sina_line(r.text, sc)
            if not data:
                continue
            results.append(IndexData(
                code=c,
                name=INDEX_NAMES.get(c, ""),
                price=float(data[1]),
                pct_chg=float(data[3]),
                change=float(data[2]),
                vol=float(data[4]) if len(data) > 4 else 0,
            ))

        return results

    def fetch_stock_quote(self, ts_code: str) -> StockQuote | None:
        code = self._to_sina_stock_code(ts_code)
        if not code:
            return None

        url = self.BASE_URL + code
        try:
            r = requests.get(url, headers=self.HEADERS, timeout=10)
            if r.status_code != 200:
                raise DataSourceError(f"Sina HTTP {r.status_code}")
        except requests.RequestException as e:
            raise DataSourceError(f"Sina unavailable: {e}") from e

        data = self._parse_sina_line(r.text, code)
        if not data or len(data) < 10:
            return None

        # 新浪个股格式:
        # 0:name 1:open 2:pre_close 3:price 4:high 5:low
        # 8:vol(手) 9:amount(万) ...
        return StockQuote(
            ts_code=ts_code,
            name=data[0],
            price=float(data[3]),
            pre_close=float(data[2]),
            pct_chg=round((float(data[3]) - float(data[2])) / float(data[2]) * 100, 4),
            change=round(float(data[3]) - float(data[2]), 3),
            open=float(data[1]),
            high=float(data[4]),
            low=float(data[5]),
            vol=float(data[8]) if len(data) > 8 else 0,
            amount=float(data[9]) * 10000 if len(data) > 9 and data[9] else 0,
        )

    @staticmethod
    def _to_sina_stock_code(ts_code: str) -> str | None:
        """600000.SH → sh600000, 000001.SZ → sz000001"""
        parts = ts_code.split(".")
        if len(parts) != 2:
            return None
        symbol, market = parts
        return f"{market.lower()}{symbol}"

    def fetch_news(self) -> list[dict]:
        """通过新浪财经 API 获取最新财经新闻。"""
        try:
            url = (
                "https://feed.mix.sina.com.cn/api/roll/get"
                "?pageid=153&lid=2509&k=&num=30&page=1"
            )
            r = requests.get(url, headers=self.HEADERS, timeout=10)
            data = r.json()
            items = data.get("result", {}).get("data", [])
            return [
                {
                    "title": item.get("title", ""),
                    "content": item.get("intro", ""),
                    "pub_time": item.get("ctime", ""),
                    "url": item.get("url", ""),
                    "source": "新浪财经",
                }
                for item in items
            ]
        except Exception as e:
            raise DataSourceError(f"Sina news failed: {e}") from e

    @staticmethod
    def _parse_sina_line(text: str, code: str) -> list[str] | None:
        """从新浪返回文本中提取指定代码的数据。"""
        pattern = rf'var hq_str_{re.escape(code)}="([^"]*)"'
        m = re.search(pattern, text)
        if not m:
            return None
        return m.group(1).split(",")
