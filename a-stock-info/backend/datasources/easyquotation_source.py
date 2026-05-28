"""easyquotation 数据源 — 批量实时行情。

封装 easyquotation 库（Sina 后端），支持批量获取全市场快照。
比逐条 HTTP 请求快 10-100 倍。
"""

import logging

from datasources.base import BaseDataSource, DataSourceError, StockQuote

logger = logging.getLogger(__name__)


class EasyQuotationSource(BaseDataSource):
    """easyquotation 批量实时行情。

    底层使用 Sina/腾讯 的实时数据接口，
    一次调用可获取多只股票的实时快照。
    """

    name = "easyquotation"
    priority = 1  # Sina 优先（含市值/换手率）

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import easyquotation
                self._client = easyquotation.use("sina")
            except ImportError:
                raise DataSourceError("easyquotation not installed")
        return self._client

    def is_available(self) -> bool:
        try:
            self._get_client()
            return True
        except Exception:
            return False

    def fetch_stock_quote(self, ts_code: str) -> StockQuote | None:
        """获取个股实时行情（通过批量接口）。"""
        symbol = ts_code.split(".")[0]
        try:
            client = self._get_client()
            data = client.stocks([symbol])
            if symbol not in data:
                return None
            return self._parse(symbol, data[symbol])
        except Exception as e:
            raise DataSourceError(f"easyquotation quote failed: {e}") from e

    def fetch_stock_quotes(self, ts_codes: list[str]) -> list[StockQuote]:
        """批量获取多只股票实时行情。"""
        symbols = [c.split(".")[0] for c in ts_codes]
        try:
            client = self._get_client()
            data = client.stocks(symbols)
        except Exception as e:
            raise DataSourceError(f"easyquotation batch failed: {e}") from e

        results = []
        for ts_code in ts_codes:
            symbol = ts_code.split(".")[0]
            if symbol in data:
                q = self._parse(symbol, data[symbol])
                if q:
                    results.append(q)
        return results

    def fetch_indices(self, codes: list[str]) -> list:
        """获取指数行情 — 适配 BaseDataSource 接口。"""
        from datasources.base import IndexData
        raw = self.fetch_index_quotes()
        result = [IndexData(**r) for r in raw if r["code"] in codes]
        if not result:
            raise DataSourceError("easyquotation: no matching indices")
        return result

    def fetch_index_quotes(self) -> list[dict]:
        """获取三大指数实时行情。"""
        try:
            client = self._get_client()
            data = client.stocks(["sh000001", "sz399001", "sz399006"])
            results = []
            idx_map = {
                "sh000001": ("000001.SH", "上证指数"),
                "sz399001": ("399001.SZ", "深证成指"),
                "sz399006": ("399006.SZ", "创业板指"),
            }
            for raw_code, (code, name) in idx_map.items():
                if raw_code in data:
                    d = data[raw_code]
                    price = d.get("now", 0)
                    close = d.get("close", price)
                    results.append({
                        "code": code,
                        "name": name,
                        "price": price,
                        "pct_chg": round((price - close) / close * 100, 4) if close else None,
                        "change": round(price - close, 3) if close else None,
                        "vol": d.get("volume", 0),
                    })
            return results
        except Exception as e:
            raise DataSourceError(f"easyquotation index failed: {e}") from e

    @staticmethod
    def _parse(symbol: str, d: dict) -> StockQuote | None:
        """解析 easyquotation 返回的字典。"""
        try:
            price = d.get("now", 0)
            pre_close = d.get("close", price)
            # easyquotation Sina 字段：
            #   volume = 成交量(股), turnover = 成交额(元), 无换手率
            vol = d.get("volume", 0)
            amount = d.get("turnover", 0)  # 注意：turnover 是成交额
            return StockQuote(
                ts_code=symbol,
                name=d.get("name", symbol),
                price=price,
                pre_close=pre_close,
                pct_chg=round((price - pre_close) / pre_close * 100, 4) if pre_close else 0,
                change=round(price - pre_close, 3),
                open=d.get("open", price),
                high=d.get("high", price),
                low=d.get("low", price),
                vol=vol,
                amount=amount,
                turnover_rate=None,
                total_mv=None,
                circ_mv=None,
            )
        except Exception:
            return None
