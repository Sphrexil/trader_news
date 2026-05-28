"""数据源基类 — 所有数据源继承此类，实现统一接口。

轮动机制：DataSourceManager 按优先级顺序尝试各数据源，失败则自动切换下一个。
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class IndexData:
    code: str
    name: str
    price: float
    pct_chg: float
    change: float
    vol: float


@dataclass
class StockQuote:
    ts_code: str
    name: str
    price: float
    pre_close: float
    pct_chg: float
    change: float
    open: float
    high: float
    low: float
    vol: float
    amount: float
    turnover_rate: float | None = None
    total_mv: float | None = None
    circ_mv: float | None = None


class DataSourceError(Exception):
    """数据源不可用时抛出。"""
    pass


class BaseDataSource(ABC):
    """数据源抽象基类。

    name: 数据源名称，用于日志标识。
    priority: 优先级，数字越小越优先使用。
    """

    name: str = "base"
    priority: int = 100

    def is_available(self) -> bool:
        """检查数据源是否可用（子类可覆写，默认返回 True）。"""
        return True

    def fetch_indices(self, codes: list[str]) -> list[IndexData]:
        """获取指数行情。子类可选覆写，默认返回空列表表示不支持。"""
        return []

    def fetch_stock_quote(self, ts_code: str) -> StockQuote | None:
        """获取个股实时行情（可选实现）。"""
        return None

    def fetch_stock_quotes(self, ts_codes: list[str]) -> list[StockQuote]:
        """批量获取个股行情（可选实现，默认逐个调用 fetch_stock_quote）。"""
        results = []
        for code in ts_codes:
            try:
                q = self.fetch_stock_quote(code)
                if q:
                    results.append(q)
            except DataSourceError:
                continue
        return results

    def fetch_daily_prices(
        self, ts_code: str, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """获取个股历史日K线。默认抛出 DataSourceError，子类覆写。"""
        raise DataSourceError(f"{self.name}: fetch_daily_prices not implemented")

    def fetch_index_daily(
        self, code: str, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """获取指数日K线。默认抛出 DataSourceError，子类覆写。"""
        raise DataSourceError(f"{self.name}: fetch_index_daily not implemented")

    def fetch_sectors(self) -> list[dict]:
        """获取行业板块数据。默认抛出 DataSourceError，子类覆写。"""
        raise DataSourceError(f"{self.name}: fetch_sectors not implemented")

    def fetch_news(self) -> list[dict]:
        """获取财经新闻。默认抛出 DataSourceError，子类覆写。"""
        raise DataSourceError(f"{self.name}: fetch_news not implemented")
