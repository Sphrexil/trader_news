"""数据源管理器 — 轮动式故障切换。

按优先级依次尝试各数据源，成功则返回，失败则自动切换到下一个。
结果会缓存到 Redis/内存，减少重复请求。
"""

import logging
from collections.abc import Callable
from typing import Any

from cache import get_cache
from datasources.base import BaseDataSource, DataSourceError, IndexData, StockQuote
from datasources.sina_source import SinaDataSource
from datasources.baostock_source import BaoStockSource
from datasources.akshare_source import AKShareSource

logger = logging.getLogger(__name__)


class DataSourceManager:
    """轮动式数据源管理器。

    自动按优先级顺序尝试数据源，支持结果缓存。
    """

    def __init__(self):
        self.sources: list[BaseDataSource] = [
            SinaDataSource(),
            BaoStockSource(),
            AKShareSource(),
        ]
        self.sources.sort(key=lambda s: s.priority)
        self._cache = get_cache()

    def _try_sources(self, method: str, *args, **kwargs) -> Any:
        """轮动调用各数据源的指定方法。

        按 priority 顺序尝试，遇到 DataSourceError 则切换下一个。
        全部失败则抛出最后一个异常。
        """
        last_error = None
        for source in self.sources:
            if not source.is_available():
                logger.debug(f"[{source.name}] 不可用，跳过")
                continue

            fn: Callable | None = getattr(source, method, None)
            if fn is None:
                continue

            try:
                result = fn(*args, **kwargs)
                logger.info(f"[{source.name}] {method} 成功")
                return result
            except DataSourceError as e:
                logger.warning(f"[{source.name}] {method} 失败: {e}")
                last_error = e
                continue
            except Exception as e:
                logger.warning(f"[{source.name}] {method} 异常: {type(e).__name__}: {e}")
                last_error = DataSourceError(str(e))
                continue

        raise last_error or DataSourceError(f"All sources failed for {method}")

    # ── 公开接口 ───────────────────────────────────

    def get_indices(
        self, codes: list[str] | None = None, ttl: int = 60
    ) -> list[IndexData]:
        """获取指数行情（带缓存）。

        默认指数: 上证, 深证, 创业板, 北证50
        """
        if codes is None:
            codes = ["000001.SH", "399001.SZ", "399006.SZ", "899050.BJ"]

        cache_key = "ds:indices:" + ",".join(codes)
        cached = self._cache.get(cache_key)
        if cached:
            return [IndexData(**d) for d in cached]

        results = self._try_sources("fetch_indices", codes)
        if results:
            self._cache.set(cache_key, [r.__dict__ for r in results], ttl)
        return results or []

    def get_stock_quote(self, ts_code: str) -> StockQuote | None:
        """获取个股实时行情。"""
        cache_key = f"ds:quote:{ts_code}"
        cached = self._cache.get(cache_key)
        if cached:
            return StockQuote(**cached)

        try:
            result = self._try_sources("fetch_stock_quote", ts_code)
            if result:
                self._cache.set(cache_key, result.__dict__, 30)
            return result
        except DataSourceError:
            return None

    def get_index_daily(
        self, code: str, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """获取指数日K线（用于大盘概况计算）。"""
        return self._try_sources("fetch_index_daily", code, start_date, end_date)

    def get_daily_prices(
        self, ts_code: str, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """获取个股日K线。"""
        cache_key = f"ds:kline:{ts_code}:{start_date}:{end_date}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        try:
            result = self._try_sources("fetch_daily_prices", ts_code, start_date, end_date)
            if result:
                self._cache.set(cache_key, result, 300)
            return result or []
        except DataSourceError:
            return []

    def get_news(self, ttl: int = 120) -> list[dict]:
        """获取最新财经新闻（轮动数据源）。"""
        cache_key = "ds:news"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        try:
            result = self._try_sources("fetch_news")
            if result:
                self._cache.set(cache_key, result, ttl)
            return result or []
        except DataSourceError:
            return []

    def get_sectors(self, ttl: int = 180) -> list[dict]:
        """获取行业板块涨跌数据（带缓存）。"""
        cache_key = "ds:sectors"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        try:
            result = self._try_sources("fetch_sectors")
            if result:
                self._cache.set(cache_key, result, ttl)
            return result or []
        except DataSourceError:
            return []

    def get_financials(self, symbol: str, ttl: int = 600) -> list[dict]:
        """获取个股财务数据（带缓存）。symbol: 纯数字代码，如 601991"""
        cache_key = f"ds:financials:{symbol}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        try:
            result = self._try_sources("fetch_financials", symbol)
            if result:
                self._cache.set(cache_key, result, ttl)
            return result or []
        except DataSourceError:
            return []

    def get_announcements(self, symbol: str, ttl: int = 300) -> list[dict]:
        """获取个股公告列表（带缓存）。symbol: 纯数字代码，如 601991"""
        cache_key = f"ds:announcements:{symbol}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        try:
            result = self._try_sources("fetch_announcements", symbol)
            if result:
                self._cache.set(cache_key, result, ttl)
            return result or []
        except DataSourceError:
            return []


# 单例
_ds_manager: DataSourceManager | None = None


def get_ds_manager() -> DataSourceManager:
    global _ds_manager
    if _ds_manager is None:
        _ds_manager = DataSourceManager()
    return _ds_manager
