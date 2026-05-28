"""数据源管理器 — 轮动式故障切换。

按优先级依次尝试各数据源，成功则返回，失败则自动切换到下一个。
结果会缓存到 Redis/内存，减少重复请求。
"""

import logging
from datetime import date
from collections.abc import Callable
from typing import Any

from cache import get_cache
from datasources.base import BaseDataSource, DataSourceError, IndexData, StockQuote
from datasources.easyquotation_source import EasyQuotationSource
from datasources.sina_source import SinaDataSource
from datasources.baostock_source import BaoStockSource
from datasources.akshare_source import AKShareSource
from datasources.wallstreetcn_source import WallStreetCNSource

logger = logging.getLogger(__name__)


class DataSourceManager:
    """轮动式数据源管理器。

    自动按优先级顺序尝试数据源，支持结果缓存。
    """

    def __init__(self):
        self.sources: list[BaseDataSource] = [
            EasyQuotationSource(),
            SinaDataSource(),
            BaoStockSource(),
            AKShareSource(),
            WallStreetCNSource(),
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
        """获取个股日K线。

        对单个数据源返回的脏数据做清洗，避免把 null / 单日残缺结果当成有效 K 线。
        """
        min_required = 2
        try:
            if date.fromisoformat(start_date) == date.fromisoformat(end_date):
                min_required = 1
        except Exception:
            pass

        best: list[dict[str, Any]] = []
        last_error = None
        for source in self.sources:
            if not source.is_available():
                continue

            fn: Callable | None = getattr(source, "fetch_daily_prices", None)
            if fn is None:
                continue

            try:
                result = fn(ts_code, start_date, end_date)
                cleaned = self._validate_daily_prices(result)
                if len(cleaned) >= min_required:
                    if len(cleaned) > len(best):
                        best = cleaned
                    continue

                logger.warning(
                    f"[{source.name}] daily_prices returned insufficient batch "
                    f"for {ts_code} ({len(cleaned)} valid rows)"
                )
                last_error = DataSourceError(f"{source.name} returned insufficient daily prices")
            except DataSourceError as e:
                logger.warning(f"[{source.name}] fetch_daily_prices 失败: {e}")
                last_error = e
            except Exception as e:
                logger.warning(f"[{source.name}] fetch_daily_prices 异常: {type(e).__name__}: {e}")
                last_error = DataSourceError(str(e))

        if best:
            return best
        return []

    @staticmethod
    def _validate_daily_prices(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        """过滤掉缺失 OHLC 的脏 K 线，并去重排序。"""
        if not rows:
            return []

        cleaned: list[dict[str, Any]] = []
        seen_dates: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            date = str(row.get("date", ""))[:10]
            if not date or date in seen_dates:
                continue

            try:
                open_v = float(row["open"])
                high_v = float(row["high"])
                low_v = float(row["low"])
                close_v = float(row["close"])
            except (TypeError, ValueError, KeyError):
                continue

            if min(open_v, high_v, low_v, close_v) <= 0:
                continue
            if high_v < max(open_v, close_v, low_v) or low_v > min(open_v, close_v, high_v):
                continue

            seen_dates.add(date)
            normalized = dict(row)
            normalized["date"] = date
            normalized["open"] = open_v
            normalized["high"] = high_v
            normalized["low"] = low_v
            normalized["close"] = close_v
            cleaned.append(normalized)

        cleaned.sort(key=lambda x: str(x.get("date", "")))
        return cleaned

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
                # 为领涨股补充 ts_code（通过名称反查）
                from database import SessionLocal
                from models.stock import Stock
                db = SessionLocal()
                try:
                    names = {s["lead_stock"]["name"] for s in result if s.get("lead_stock", {}).get("name")}
                    stocks = db.query(Stock).filter(Stock.name.in_(names)).all()
                    name_map = {s.name: s.ts_code for s in stocks}
                    for sector in result:
                        ls = sector.get("lead_stock", {})
                        if ls and not ls.get("ts_code"):
                            ls["ts_code"] = name_map.get(ls.get("name"))
                finally:
                    db.close()

                self._cache.set(cache_key, result, ttl)
            return result or []
        except DataSourceError:
            return []

    def get_minute_kline(self, ts_code: str, freq: str = "1") -> list[dict]:
        """获取分钟K线（腾讯数据源）。freq: 1/5/15/30/60"""
        cache_key = f"ds:minute:{ts_code}:{freq}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached
        try:
            result = self._try_sources("fetch_minute_kline", ts_code, freq)
            if result:
                self._cache.set(cache_key, result, 60)
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
