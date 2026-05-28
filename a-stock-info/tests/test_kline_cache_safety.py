"""K线缓存与清洗安全测试。"""

from cache import Cache
from datasources.manager import DataSourceManager
from services.price_service import PriceService


def test_cache_does_not_persist_none():
    cache = Cache()
    cache._redis = None

    cache.set("kline:test:none", None)

    assert cache.get("kline:test:none") is None
    assert cache._memory.get("kline:test:none") is None


def test_daily_prices_validation_filters_dirty_rows():
    rows = [
        {"date": "2026-05-01", "open": None, "high": None, "low": None, "close": None},
        {"date": "2026-05-02", "open": 10, "high": 10.5, "low": 9.8, "close": 10.1},
        {"date": "2026-05-02", "open": 10, "high": 10.5, "low": 9.8, "close": 10.1},
        {"date": "2026-05-03", "open": 0, "high": 0, "low": 0, "close": 0},
    ]

    cleaned = DataSourceManager._validate_daily_prices(rows)

    assert len(cleaned) == 1
    assert cleaned[0]["date"] == "2026-05-02"
    assert cleaned[0]["close"] == 10.1


def test_kline_cleaner_rejects_dirty_single_row():
    items = [
        {"date": "2026-05-01", "open": None, "high": None, "low": None, "close": None},
        {"date": "2026-05-02", "open": 10, "high": 10.5, "low": 9.8, "close": 10.1},
    ]

    cleaned = PriceService._normalize_kline_items(items)

    assert len(cleaned) == 1
    assert cleaned[0]["date"] == "2026-05-02"


def test_daily_kline_requires_more_than_one_row_for_normal_query():
    items = [
        {"date": "2026-05-02", "open": 10, "high": 10.5, "low": 9.8, "close": 10.1},
    ]

    assert PriceService._accept_daily_kline(items, None, None) is False
    assert PriceService._accept_daily_kline(items, "2026-05-02", "2026-05-02") is True
