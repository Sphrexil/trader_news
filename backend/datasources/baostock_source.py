"""BaoStock 数据源 — 免费、注册即用、支持历史K线和指数。"""

import logging
from typing import Any

from datasources.base import BaseDataSource, DataSourceError

logger = logging.getLogger(__name__)


class BaoStockSource(BaseDataSource):
    """BaoStock 数据接口。

    免费注册，无需付费 Token。
    支持: 历史K线（日/周/月）、指数日K线、复权数据。
    不支持: 实时行情。
    """

    name = "baostock"
    priority = 2

    BAOSTOCK_INDEX_MAP = {
        "000001.SH": "sh.000001",
        "399001.SZ": "sz.399001",
        "399006.SZ": "sz.399006",
    }

    def __init__(self):
        self._logged_in = False

    def is_available(self) -> bool:
        try:
            import baostock as bs
            lg = bs.login()
            if lg.error_code == "0":
                bs.logout()
                return True
            return False
        except ImportError:
            return False

    def _ensure_login(self):
        if self._logged_in:
            return
        import baostock as bs
        lg = bs.login()
        if lg.error_code != "0":
            raise DataSourceError(f"BaoStock login failed: {lg.error_msg}")
        self._logged_in = True

    def _logout(self):
        if self._logged_in:
            import baostock as bs
            bs.logout()
            self._logged_in = False

    def fetch_index_daily(
        self, code: str, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """获取指数日K线（用于计算大盘概况）。"""
        bs_code = self.BAOSTOCK_INDEX_MAP.get(code)
        if not bs_code:
            return []

        try:
            import baostock as bs

            self._ensure_login()
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,volume,amount,pctChg",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
            )
            rows: list[dict[str, Any]] = []
            while rs.next():
                row = rs.get_row_data()
                rows.append({
                    "date": row[0],
                    "open": float(row[1]) if row[1] else None,
                    "high": float(row[2]) if row[2] else None,
                    "low": float(row[3]) if row[3] else None,
                    "close": float(row[4]) if row[4] else None,
                    "volume": float(row[5]) if row[5] else None,
                    "amount": float(row[6]) if row[6] else None,
                    "pct_chg": float(row[7]) if row[7] else None,
                })
            return rows
        except ImportError:
            raise DataSourceError("baostock not installed")
        except Exception as e:
            raise DataSourceError(f"BaoStock query failed: {e}") from e

    def fetch_daily_prices(
        self, ts_code: str, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """获取个股日K线。"""
        parts = ts_code.split(".")
        if len(parts) != 2:
            return []
        symbol, market = parts
        bs_code = f"{market.lower()}.{symbol}"

        try:
            import baostock as bs

            self._ensure_login()
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,preclose,volume,amount,turn,peTTM",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="2",  # 前复权
            )
            rows: list[dict[str, Any]] = []
            while rs.next():
                row = rs.get_row_data()
                rows.append({
                    "date": row[0],
                    "open": float(row[1]) if row[1] else None,
                    "high": float(row[2]) if row[2] else None,
                    "low": float(row[3]) if row[3] else None,
                    "close": float(row[4]) if row[4] else None,
                    "pre_close": float(row[5]) if row[5] else None,
                    "volume": float(row[6]) if row[6] else None,
                    "amount": float(row[7]) if row[7] else None,
                    "turnover_rate": float(row[8]) if row[8] else None,
                })
            return rows
        except ImportError:
            raise DataSourceError("baostock not installed")
        except Exception as e:
            raise DataSourceError(f"BaoStock query failed: {e}") from e

    def __del__(self):
        self._logout()
