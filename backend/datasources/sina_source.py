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
    priority = 0  # 最高优先 — 含市值/换手率完整数据

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
        """获取个股实时行情（含市值/换手率）。新浪市场中心为主源。"""
        import json

        symbol = ts_code.split(".")[0]
        code_only = symbol
        sina_code = f"sh{code_only}" if ts_code.endswith(".SH") else f"sz{code_only}"

        # 1. 新浪市场中心（完整数据: 价格/量/额/市值/换手率/PE/PB）
        # 注意：symbol参数是分页起点不是过滤，需本地筛选
        try:
            mkt_url = (
                "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
                "Market_Center.getHQNodeData"
            )
            # 用相近代码作分页起点，仅拉取小范围数据
            start_sym = str(int(code_only) - 10) if code_only.isdigit() else code_only
            params = {
                "page": 1, "num": 30, "sort": "symbol", "asc": 1,
                "node": "hs_a", "symbol": start_sym,
            }
            r = requests.get(mkt_url, params=params, headers=self.HEADERS, timeout=10)
            all_items = json.loads(r.text)
            # 本地按代码筛选
            code_lower = code_only.lower()
            item = None
            for it in all_items:
                if str(it.get("code", "")) == code_only or str(it.get("symbol", "")) == sina_code:
                    item = it
                    break
            if item:
                price = float(item.get("trade", 0))
                pre_close = float(item.get("settlement", price))
                t_rate = item.get("turnoverratio")
                return StockQuote(
                    ts_code=ts_code,
                    name=item.get("name", ts_code),
                    price=price,
                    pre_close=pre_close,
                    pct_chg=float(item.get("changepercent", 0)),
                    change=float(item.get("pricechange", 0)),
                    open=float(item.get("open", price)),
                    high=float(item.get("high", price)),
                    low=float(item.get("low", price)),
                    vol=float(item.get("volume", 0)),
                    amount=float(item.get("amount", 0)) * 10000,  # 万元→元
                    turnover_rate=float(t_rate) if t_rate and t_rate != "0.00000" else None,
                    total_mv=float(item["mktcap"]) if item.get("mktcap") else None,
                    circ_mv=float(item["nmc"]) if item.get("nmc") else None,
                )
        except (requests.RequestException, json.JSONDecodeError, KeyError, ValueError):
            pass

        # 2. 降级：新浪基础行情接口（无市值/换手率）
        url = self.BASE_URL + sina_code
        try:
            r = requests.get(url, headers=self.HEADERS, timeout=5)
            if r.status_code != 200:
                raise DataSourceError(f"Sina HTTP {r.status_code}")
        except requests.RequestException as e:
            raise DataSourceError(f"Sina unavailable: {e}") from e

        data = self._parse_sina_line(r.text, sina_code)
        if not data or len(data) < 10:
            return None

        price = float(data[3])
        pre_close = float(data[2])
        return StockQuote(
            ts_code=ts_code,
            name=data[0],
            price=price,
            pre_close=pre_close,
            pct_chg=round((price - pre_close) / pre_close * 100, 4) if pre_close else 0,
            change=round(price - pre_close, 3),
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

    def fetch_daily_prices(
        self, ts_code: str, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """通过新浪 K 线 API 获取日线数据。"""
        import json

        sina_code = self._to_sina_stock_code(ts_code)
        if not sina_code:
            raise DataSourceError(f"Invalid stock code: {ts_code}")

        try:
            url = (
                "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
                f"CN_MarketData.getKLineData?symbol={sina_code}&scale=240&ma=no&datalen=200"
            )
            r = requests.get(url, headers=self.HEADERS, timeout=10)
            if r.status_code != 200 or not r.text:
                raise DataSourceError(f"Sina K-line HTTP {r.status_code}")

            raw = json.loads(r.text)
            if not raw or not isinstance(raw, list):
                raise DataSourceError("Sina K-line returned empty")

            items = []
            for point in raw:
                d = point.get("day", "")
                if d < start_date.replace("-", "") or d > end_date.replace("-", ""):
                    continue
                items.append({
                    "date": f"{d[:4]}-{d[4:6]}-{d[6:8]}",
                    "open": float(point.get("open", 0)),
                    "high": float(point.get("high", 0)),
                    "low": float(point.get("low", 0)),
                    "close": float(point.get("close", 0)),
                    "volume": float(point.get("volume", 0)),
                    "amount": None,
                    "turnover_rate": None,
                })
            if not items:
                raise DataSourceError("Sina K-line: no data in range")
            return items
        except (requests.RequestException, json.JSONDecodeError, ValueError) as e:
            raise DataSourceError(f"Sina K-line failed: {e}") from e

    @staticmethod
    def _parse_sina_line(text: str, code: str) -> list[str] | None:
        """从新浪返回文本中提取指定代码的数据。"""
        pattern = rf'var hq_str_{re.escape(code)}="([^"]*)"'
        m = re.search(pattern, text)
        if not m:
            return None
        return m.group(1).split(",")
