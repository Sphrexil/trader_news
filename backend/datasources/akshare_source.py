"""AKShare 数据源 — 覆盖最广，但部分接口对网络有要求。"""

import logging

from datasources.base import BaseDataSource, DataSourceError, IndexData

logger = logging.getLogger(__name__)


class AKShareSource(BaseDataSource):
    """AKShare 数据接口。

    功能最全：股票列表、日行情、财务数据、新闻、公告等。
    部分接口（东方财富系）需要稳定的网络连接。
    """

    name = "akshare"
    priority = 3

    def is_available(self) -> bool:
        try:
            import akshare as ak
            return True
        except ImportError:
            return False

    def fetch_indices(self, codes: list[str]) -> list[IndexData]:
        """通过 AKShare 获取指数行情（批量接口）。"""
        try:
            import akshare as ak

            df = ak.stock_zh_index_spot_em()
            if df.empty:
                raise DataSourceError("AKShare index spot returned empty")

            results = []
            for _, row in df.iterrows():
                code = str(row.get("代码", ""))
                name = str(row.get("名称", ""))

                if code == "000001":
                    idx_code = "000001.SH"
                    idx_name = "上证指数"
                elif code == "399001":
                    idx_code = "399001.SZ"
                    idx_name = "深证成指"
                elif code == "399006":
                    idx_code = "399006.SZ"
                    idx_name = "创业板指"
                elif code == "899050":
                    idx_code = "899050.BJ"
                    idx_name = "北证50"
                else:
                    continue

                if idx_code not in codes:
                    continue

                results.append(IndexData(
                    code=idx_code,
                    name=idx_name,
                    price=float(row["最新价"]),
                    pct_chg=float(row["涨跌幅"]),
                    change=float(row["涨跌额"]),
                    vol=float(row["成交量"]) if row.get("成交量") else 0,
                ))

            if not results:
                raise DataSourceError("AKShare: no matching indices found")
            return results
        except ImportError:
            raise DataSourceError("akshare not installed")
        except DataSourceError:
            raise
        except Exception as e:
            raise DataSourceError(f"AKShare index failed: {e}") from e

    def fetch_sectors(self) -> list[dict]:
        """通过同花顺接口获取行业板块涨跌数据。"""
        try:
            import akshare as ak

            df = ak.stock_board_industry_summary_ths()
            if df.empty:
                raise DataSourceError("THS sectors empty")

            cols = list(df.columns)
            sectors = []
            for _, row in df.iterrows():
                vals = [row[c] for c in cols]
                sectors.append({
                    "name": str(vals[1]),
                    "pct_chg": float(vals[2]),
                    "change_amount": float(vals[3]) if vals[3] else None,
                    "up_count": int(vals[6]),
                    "down_count": int(vals[7]),
                    "lead_stock": {
                        "name": str(vals[9]),
                        "price": float(vals[10]) if vals[10] else None,
                        "pct_chg": float(vals[11]) if vals[11] else None,
                    },
                })
            return sectors
        except ImportError:
            raise DataSourceError("akshare not installed")
        except DataSourceError:
            raise
        except Exception as e:
            raise DataSourceError(f"AKShare sectors failed: {e}") from e

    def fetch_news(self) -> list[dict]:
        """通过同花顺接口获取最新全球财经新闻。"""
        try:
            import akshare as ak

            df = ak.stock_info_global_ths()
            if df.empty:
                raise DataSourceError("THS news empty")

            cols = list(df.columns)
            items = []
            for _, row in df.iterrows():
                vals = [row[c] for c in cols]
                items.append({
                    "title": str(vals[0]),
                    "content": str(vals[1]) if vals[1] else "",
                    "pub_time": str(vals[2]) if vals[2] else "",
                    "url": str(vals[3]) if len(vals) > 3 and vals[3] else "",
                    "source": "同花顺",
                })
            return items
        except ImportError:
            raise DataSourceError("akshare not installed")
        except DataSourceError:
            raise
        except Exception as e:
            raise DataSourceError(f"AKShare news failed: {e}") from e

    def fetch_financials(self, symbol: str) -> list[dict]:
        """通过同花顺接口获取财务数据。"""
        try:
            import akshare as ak

            df = ak.stock_financial_abstract_ths(symbol=symbol, indicator="按单季度")
            if df.empty:
                raise DataSourceError(f"THS financials empty for {symbol}")

            cols = list(df.columns)
            items = []
            for _, row in df.iterrows():
                vals = [row[c] for c in cols]
                items.append({
                    "period": str(vals[0]),           # 报告期
                    "net_profit": self._parse_num(vals[1]),   # 净利润
                    "net_profit_yoy": self._parse_pct(vals[2]),  # 净利润同比增长率
                    "deducted_profit": self._parse_num(vals[3]),  # 扣非净利润
                    "deducted_yoy": self._parse_pct(vals[4]),     # 扣非同比增长率
                    "revenue": self._parse_num(vals[5]),          # 营业总收入
                    "revenue_yoy": self._parse_pct(vals[6]),      # 营收同比增长率
                    "eps": self._parse_num(vals[7]),              # 基本每股收益
                })
            return items
        except ImportError:
            raise DataSourceError("akshare not installed")
        except DataSourceError:
            raise
        except Exception as e:
            raise DataSourceError(f"AKShare financials failed: {e}") from e

    def fetch_announcements(self, symbol: str) -> list[dict]:
        """通过东方财富 API 获取最新公告。"""
        try:
            import requests

            url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
            params = {
                "sr": -1, "page_size": 30, "page_index": 1,
                "ann_type": "A", "client_source": "web",
                "stock_list": symbol,
            }
            r = requests.get(url, params=params, timeout=10, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://data.eastmoney.com/",
            })
            data = r.json()
            raw_list = data.get("data", {}).get("list", [])

            items = []
            for item in raw_list:
                notice_date = item.get("notice_date", "")[:10]
                title = item.get("title_cht", "") or item.get("title", "")
                ann_id = item.get("art_code", "")
                url = f"https://data.eastmoney.com/notices/detail/{symbol}/{ann_id}.html" if ann_id else ""
                items.append({
                    "ts_code": f"{symbol}.SH" if symbol.startswith("6") else f"{symbol}.SZ",
                    "title": title.strip(),
                    "pub_date": notice_date,
                    "url": url,
                })
            return items
        except ImportError:
            raise DataSourceError("requests not available")
        except DataSourceError:
            raise
        except Exception as e:
            raise DataSourceError(f"EastMoney announcements failed: {e}") from e

    def fetch_minute_kline(self, ts_code: str, freq: str = "1") -> list[dict]:
        """获取分钟K线（腾讯数据源）。freq: 1/5/15/30/60"""
        try:
            import akshare as ak
            prefix = "sh" if ts_code.endswith(".SH") else "sz"
            symbol_raw = ts_code.split(".")[0]
            symbol = f"{prefix}{symbol_raw}"

            df = ak.stock_zh_a_minute(symbol=symbol, period=freq)
            if df.empty:
                raise DataSourceError(f"Tencent minute kline empty for {ts_code}")

            cols = list(df.columns)
            items = []
            for _, row in df.iterrows():
                vals = [row[c] for c in cols]
                items.append({
                    "time": str(vals[0]),
                    "open": float(vals[1]) if vals[1] else None,
                    "high": float(vals[2]) if vals[2] else None,
                    "low": float(vals[3]) if vals[3] else None,
                    "close": float(vals[4]) if vals[4] else None,
                    "vol": float(vals[5]) if len(vals) > 5 and vals[5] else 0,
                })
            return items
        except ImportError:
            raise DataSourceError("akshare not installed")
        except DataSourceError:
            raise
        except Exception as e:
            raise DataSourceError(f"Tencent minute kline failed: {e}") from e

    def fetch_stock_list(self) -> list[dict]:
        """获取全量 A 股股票列表。"""
        try:
            import akshare as ak

            df = ak.stock_info_a_code_name()
            codes = []
            for _, row in df.iterrows():
                code = str(row.get("code", ""))
                if not code:
                    continue
                if code.startswith("6"):
                    market = "SH"
                    ts_code = f"{code}.SH"
                elif code.startswith("0") or code.startswith("3"):
                    market = "SZ"
                    ts_code = f"{code}.SZ"
                elif code.startswith("8") or code.startswith("4"):
                    market = "BJ"
                    ts_code = f"{code}.BJ"
                else:
                    continue
                codes.append({
                    "ts_code": ts_code,
                    "name": str(row.get("name", "")),
                    "market": market,
                })
            return codes
        except ImportError:
            raise DataSourceError("akshare not installed")
        except Exception as e:
            raise DataSourceError(f"AKShare stock list failed: {e}") from e

    @staticmethod
    def _parse_num(val: any) -> float | None:
        """解析带中文单位的数字，如 '28.93亿' -> 2893000000"""
        if val is None or val == "":
            return None
        s = str(val)
        try:
            if "亿" in s:
                return float(s.replace("亿", "")) * 100000000
            if "万" in s:
                return float(s.replace("万", "")) * 10000
            return float(s)
        except ValueError:
            return None

    @staticmethod
    def _parse_pct(val: any) -> float | None:
        """解析百分比字符串，如 '29.26%' -> 29.26"""
        if val is None or val == "":
            return None
        try:
            return float(str(val).replace("%", ""))
        except ValueError:
            return None
