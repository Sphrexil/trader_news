"""行情业务逻辑。"""

import logging
from datetime import date, datetime, time

import pytz
from sqlalchemy import func
from sqlalchemy.orm import Session

from cache import get_cache
from config import get_settings
from datasources.manager import get_ds_manager
from models.daily_price import DailyPrice
from models.stock import Stock

logger = logging.getLogger(__name__)
settings = get_settings()
cache = get_cache()
CN_TZ = pytz.timezone("Asia/Shanghai")


def _is_trading_time() -> bool:
    """判断当前是否在 A 股交易时段。"""
    now = datetime.now(CN_TZ)
    t = now.time()
    return time.fromisoformat(settings.TRADING_START) <= t <= time.fromisoformat(settings.TRADING_END)


class PriceService:
    """行情查询服务。"""

    def __init__(self, db: Session):
        self.db = db

    def get_latest_daily_price(self, ts_code: str) -> DailyPrice | None:
        """获取某股票最新一条日行情记录。"""
        return (
            self.db.query(DailyPrice)
            .filter(DailyPrice.ts_code == ts_code)
            .order_by(DailyPrice.trade_date.desc())
            .first()
        )

    def get_quote(self, ts_code: str) -> dict | None:
        """获取实时行情快照。

        优先级：Redis > 数据库日行情 > 轮动数据源实时行情
        所有路径最终经过统一的兜底计算，确保 amount/turnover_rate 不缺失。
        """
        stock = self.db.query(Stock).filter(Stock.ts_code == ts_code).first()
        if not stock:
            return None

        # 懒加载总股本 + 流通股本（多API兜底，首次查询时写入DB）
        if stock.total_share is None or stock.float_share is None:
            symbol = ts_code.split(".")[0]
            market = ts_code.split(".")[1].lower() if "." in ts_code else "sh"
            # API1: Sina 市场中心（最稳定）→ API2: AKShare em → API3: cninfo
            for api_fn, kwargs in [
                (_fetch_shares_sina, {"symbol": symbol, "market": market}),
                (_fetch_shares_em, {"symbol": symbol}),
                (_fetch_shares_cninfo, {"symbol": symbol}),
            ]:
                try:
                    total, fl = api_fn(**kwargs)
                    if total and stock.total_share is None:
                        stock.total_share = total
                    if fl and stock.float_share is None:
                        stock.float_share = fl
                    if total or fl:
                        self.db.flush()
                        self.db.commit()
                        break
                except Exception:
                    continue

        # ── 路径1: Redis 缓存 ──
        rt_key = f"rt:quote:{ts_code}"
        cached = cache.get(rt_key)
        if cached:
            price = cached.get("price")
            pre_close = cached.get("pre_close")
            pct_chg = cached.get("pct_chg")
            open_v = cached.get("open")
            high = cached.get("high")
            low = cached.get("low")
            vol = cached.get("vol")
            amount = cached.get("amount")
            turnover = cached.get("turnover_rate")
            total_mv = cached.get("total_mv")
            circ_mv = cached.get("circ_mv")
            qt = cached.get("quote_time")
            is_trading = _is_trading_time()
            result = self._build_quote_result(
                ts_code, stock, price, pre_close, pct_chg, open_v, high, low,
                vol, amount, turnover, total_mv, circ_mv, qt, is_trading,
            )
            result["is_trading"] = is_trading
            return result

        # ── 路径2: 数据库日行情 ──
        dp = self.get_latest_daily_price(ts_code)

        # ── 路径3: 轮动数据源实时行情 ──
        ds_quote = None
        if not dp:
            try:
                ds = get_ds_manager()
                ds_quote = ds.get_stock_quote(ts_code)
            except Exception:
                pass

        if not dp and not ds_quote:
            return {
                "ts_code": ts_code,
                "name": stock.name,
                "price": None,
                "pre_close": None,
                "pct_chg": None,
                "change": None,
                "open": None,
                "high": None,
                "low": None,
                "vol": None,
                "amount": None,
                "turnover_rate": None,
                "total_mv": None,
                "circ_mv": None,
                "quote_time": None,
                "is_trading": _is_trading_time(),
            }

        if dp:
            price = float(dp.close) if dp.close else None
            pre_close = float(dp.pre_close) if dp.pre_close else None
            pct_chg = float(dp.pct_chg) if dp.pct_chg else None
            open_v = float(dp.open) if dp.open else None
            high = float(dp.high) if dp.high else None
            low = float(dp.low) if dp.low else None
            vol = float(dp.vol) if dp.vol else None
            amount = float(dp.amount) if dp.amount else None
            turnover = float(dp.turnover_rate) if dp.turnover_rate else None
            total_mv = float(dp.total_mv) if dp.total_mv else None
            circ_mv = float(dp.circ_mv) if dp.circ_mv else None
            qt = datetime.combine(dp.trade_date, time(15, 0), tzinfo=CN_TZ)
        else:
            price = ds_quote.price
            pre_close = ds_quote.pre_close
            pct_chg = ds_quote.pct_chg
            open_v = ds_quote.open
            high = ds_quote.high
            low = ds_quote.low
            vol = ds_quote.vol
            amount = ds_quote.amount
            turnover = ds_quote.turnover_rate
            total_mv = ds_quote.total_mv
            circ_mv = ds_quote.circ_mv
            qt = datetime.now(CN_TZ)

        return self._build_quote_result(
            ts_code, stock, price, pre_close, pct_chg, open_v, high, low,
            vol, amount, turnover, total_mv, circ_mv, qt, _is_trading_time(),
        )

    @staticmethod
    def _normalize_kline_items(items: list[dict]) -> list[dict]:
        """清洗 K 线数据，移除缺失 OHLC 的脏行并按日期去重。"""
        cleaned: list[dict] = []
        seen_dates: set[str] = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            date_val = str(item.get("date", ""))[:10]
            if not date_val or date_val in seen_dates:
                continue
            try:
                open_v = float(item["open"])
                high_v = float(item["high"])
                low_v = float(item["low"])
                close_v = float(item["close"])
            except (TypeError, ValueError, KeyError):
                continue
            if min(open_v, high_v, low_v, close_v) <= 0:
                continue
            if high_v < max(open_v, close_v, low_v) or low_v > min(open_v, close_v, high_v):
                continue
            normalized = dict(item)
            normalized["date"] = date_val
            normalized["open"] = open_v
            normalized["high"] = high_v
            normalized["low"] = low_v
            normalized["close"] = close_v
            cleaned.append(normalized)
            seen_dates.add(date_val)

        cleaned.sort(key=lambda x: str(x["date"]))
        return cleaned

    @staticmethod
    def _is_single_day_request(start_date: str | None, end_date: str | None) -> bool:
        """判断是否明确请求单日 K 线。"""
        if not start_date or not end_date:
            return False
        try:
            return date.fromisoformat(start_date) == date.fromisoformat(end_date)
        except Exception:
            return False

    @staticmethod
    def _accept_daily_kline(items: list[dict], start_date: str | None, end_date: str | None) -> bool:
        """日K 至少应有 2 条；仅显式单日请求时允许 1 条。"""
        if PriceService._is_single_day_request(start_date, end_date):
            return len(items) >= 1
        return len(items) >= 2

    def _build_quote_result(
        self, ts_code: str, stock: Stock,
        price, pre_close, pct_chg, open_v, high, low,
        vol, amount, turnover, total_mv, circ_mv, qt, is_trading: bool,
    ) -> dict:
        """构建行情结果，统一应用兜底计算 + 合理性校验。"""
        # 市值兜底
        if total_mv is None and price and stock.total_share:
            total_mv = round(float(stock.total_share) * price, 2)
        if circ_mv is None and price and stock.float_share:
            circ_mv = round(float(stock.float_share) * price, 2)

        # ── 成交额兜底 + 合理性校验 ──
        # 某些数据源返回的 amount 单位错误（如多乘了10000），用 vol×price 校验
        expected = round(vol * price, 2) if vol and price else None
        if amount is None:
            amount = expected
        elif expected and amount > expected * 10:
            # 异常值（可能是单位错误，10000倍），用计算值替代
            amount = expected

        # ── 换手率归一化 ──
        # 统一转为百分比格式（0.28 = 0.28%），方便前端 formatPct 直接使用
        if turnover is not None and turnover > 0:
            if turnover < 0.1:
                turnover = round(turnover * 100, 4)

        # ── 换手率兜底 ──
        if (turnover is None or turnover <= 0) and ts_code and vol and price and vol > 0:
            # 1. 优先：流通股本计算 (精确)
            if stock.float_share:
                float_g = float(stock.float_share) * 10000
                if float_g > 0:
                    turnover = round(vol / float_g * 100, 4)
            # 2. 兜底：用 total_mv/price 反推总股本 → 换手率近似值
            if (turnover is None or turnover <= 0) and total_mv and price:
                total_shares_wan = total_mv / price       # 总股本(万股)
                total_shares_gu = total_shares_wan * 10000  # 总股本(股)
                if total_shares_gu > 0:
                    turnover = round(vol / total_shares_gu * 100, 4)
            # 3. 终极兜底：Sina 实时行情
            if turnover is None or turnover <= 0:
                try:
                    ds = get_ds_manager()
                    extra = ds.get_stock_quote(ts_code)
                    if extra and extra.turnover_rate is not None and extra.turnover_rate > 0:
                        extra_t = extra.turnover_rate
                        if extra_t < 0.1:
                            extra_t = round(extra_t * 100, 4)
                        turnover = extra_t
                except Exception:
                    pass

        return {
            "ts_code": ts_code,
            "name": stock.name,
            "price": price,
            "pre_close": pre_close,
            "pct_chg": pct_chg,
            "change": round(price - pre_close, 3) if price and pre_close else None,
            "open": open_v,
            "high": high,
            "low": low,
            "vol": vol,
            "amount": amount,
            "turnover_rate": turnover,
            "total_mv": total_mv,
            "circ_mv": circ_mv,
            "quote_time": qt,
            "is_trading": is_trading,
        }

    def get_kline(
        self,
        ts_code: str,
        period: str = "daily",
        start_date: str | None = None,
        end_date: str | None = None,
        adjust: str = "qfq",
        limit: int = 500,
    ) -> dict | None:
        """获取 K 线历史数据。

        daily/weekly/monthly: DB优先 + 轮动数据源补充
        1min/5min/15min/30min/60min: 轮动数据源(腾讯分时)
        """
        # 分钟K线 → 直接走数据源
        if period in ("1", "5", "15", "30", "60", "1min", "5min", "15min", "30min", "60min"):
            freq = period.replace("min", "")
            try:
                ds = get_ds_manager()
                rows = ds.get_minute_kline(ts_code, freq)
                items = []
                for r in rows[-limit:]:
                    items.append({
                        "date": r.get("time", ""),
                        "time": r.get("time", ""),
                        "open": r.get("open"),
                        "high": r.get("high"),
                        "low": r.get("low"),
                        "close": r.get("close"),
                        "vol": r.get("vol"),
                        "amount": None,
                        "pct_chg": None,
                        "turnover_rate": None,
                        "total_mv": None,
                    })
                return {
                    "ts_code": ts_code,
                    "period": f"{freq}min",
                    "adjust": "qfq",
                    "items": items,
                    "count": len(items),
                }
            except Exception:
                return {
                    "ts_code": ts_code, "period": f"{freq}min", "adjust": "qfq",
                    "items": [], "count": 0,
                }

        dates_seen: set[str] = set()
        items: list[dict] = []

        # 1. DB 数据
        query = (
            self.db.query(DailyPrice)
            .filter(DailyPrice.ts_code == ts_code)
            .order_by(DailyPrice.trade_date.asc())
        )
        if start_date:
            query = query.filter(DailyPrice.trade_date >= date.fromisoformat(start_date))
        if end_date:
            query = query.filter(DailyPrice.trade_date <= date.fromisoformat(end_date))

        db_rows = query.all()
        for r in db_rows:
            d = str(r.trade_date) if hasattr(r.trade_date, "isoformat") else str(r.trade_date)
            dates_seen.add(d)
            items.append({
                "date": str(r.trade_date),
                "open": float(r.open) if r.open else None,
                "high": float(r.high) if r.high else None,
                "low": float(r.low) if r.low else None,
                "close": float(r.close) if r.close else None,
                "vol": float(r.vol) if r.vol else None,
                "amount": float(r.amount) if r.amount else None,
                "pct_chg": float(r.pct_chg) if r.pct_chg else None,
                "turnover_rate": float(r.turnover_rate) if r.turnover_rate else None,
                "total_mv": float(r.total_mv) if r.total_mv else None,
            })

        # 2. 轮动数据源补充缺失日期
        try:
            ds = get_ds_manager()
            s = start_date or "2026-01-01"
            e = end_date or date.today().isoformat()
            rows = ds.get_daily_prices(ts_code, s, e)
            for r in rows:
                rd = str(r.get("date", ""))[:10]
                if rd and rd not in dates_seen:
                    dates_seen.add(rd)
                    items.append({
                        "date": rd,
                        "open": r.get("open"),
                        "high": r.get("high"),
                        "low": r.get("low"),
                        "close": r.get("close"),
                        "vol": r.get("volume"),
                        "amount": r.get("amount"),
                        "pct_chg": None,
                        "turnover_rate": r.get("turnover_rate"),
                        "total_mv": None,
                    })
        except Exception:
            pass

        # 日K：附加上实时行情作为今天未完成K线
        if period == "daily":
            try:
                today_str = date.today().isoformat()
                if today_str not in dates_seen:
                    ds = get_ds_manager()
                    q = ds.get_stock_quote(ts_code)
                    if q and q.price:
                        items.append({
                            "date": today_str,
                            "open": q.open if q.open else q.price,
                            "high": q.high if q.high else q.price,
                            "low": q.low if q.low else q.price,
                            "close": q.price,
                            "vol": q.vol,
                            "amount": q.amount,
                            "pct_chg": q.pct_chg,
                            "turnover_rate": q.turnover_rate,
                            "total_mv": q.total_mv,
                        })
            except Exception:
                pass

        # 排序，取最近 limit 条
        items = self._normalize_kline_items(items)
        if period == "daily" and not self._accept_daily_kline(items, start_date, end_date):
            logger.warning(
                f"K线数据清洗后仅剩 {len(items)} 条，"
                f"已判定为脏数据并返回空结果: {ts_code}"
            )
            items = []

        items = items[-limit:]

        return {
            "ts_code": ts_code,
            "period": period,
            "adjust": adjust,
            "items": items,
            "count": len(items),
        }

    def get_market_overview(self) -> dict:
        """获取大盘概况。

        尝试从 Redis 读取，降级为数据库聚合计算。
        """
        cache_key = "market:overview"
        ttl = 60 if _is_trading_time() else 3600

        cached = cache.get(cache_key)
        if cached:
            return cached

        # 降级：从数据库计算
        try:
            latest_date = (
                self.db.query(func.max(DailyPrice.trade_date))
                .scalar()
            )

            if not latest_date:
                # DB 无数据但不影响指数展示
                indices = self._fetch_index_data()
                return {
                    "indices": indices,
                    "market_stats": {
                        "up_count": 0, "down_count": 0, "flat_count": 0,
                        "limit_up": 0, "limit_down": 0, "total_amount": None,
                    },
                    "updated_at": datetime.now(CN_TZ).isoformat(),
                }

            prices = (
                self.db.query(DailyPrice)
                .filter(DailyPrice.trade_date == latest_date)
                .all()
            )

            up_count = sum(1 for p in prices if p.pct_chg and p.pct_chg > 0)
            down_count = sum(1 for p in prices if p.pct_chg and p.pct_chg < 0)
            flat_count = sum(1 for p in prices if p.pct_chg and p.pct_chg == 0)
            limit_up = sum(1 for p in prices if p.pct_chg and p.pct_chg >= 9.9)
            limit_down = sum(1 for p in prices if p.pct_chg and p.pct_chg <= -9.9)
            total_amount = sum(float(p.amount) * 1000 for p in prices if p.amount)  # 千元 → 元

            indices = self._fetch_index_data()
            result = {
                "indices": indices,
                "market_stats": {
                    "up_count": up_count,
                    "down_count": down_count,
                    "flat_count": flat_count,
                    "limit_up": limit_up,
                    "limit_down": limit_down,
                    "total_amount": total_amount,
                },
                "updated_at": datetime.now(CN_TZ).isoformat(),
            }
            cache.set(cache_key, result, ttl)
            return result
        except Exception:
            logger.exception("计算大盘概况失败")
            return self._empty_overview()

    def _fetch_index_data(self) -> list[dict]:
        """从轮动数据源获取真实指数行情。"""
        try:
            ds = get_ds_manager()
            indices = ds.get_indices()
            return [
                {
                    "code": i.code,
                    "name": i.name,
                    "price": i.price,
                    "pct_chg": i.pct_chg,
                    "change": i.change,
                    "vol": i.vol,
                }
                for i in indices
            ]
        except Exception:
            logger.exception("获取指数行情失败")
            return self._default_indices()

    @staticmethod
    def _default_indices() -> list[dict]:
        return [
            {"code": "000001.SH", "name": "上证指数", "price": None, "pct_chg": None, "change": None, "vol": None},
            {"code": "399001.SZ", "name": "深证成指", "price": None, "pct_chg": None, "change": None, "vol": None},
            {"code": "399006.SZ", "name": "创业板指", "price": None, "pct_chg": None, "change": None, "vol": None},
            {"code": "899050.BJ", "name": "北证50", "price": None, "pct_chg": None, "change": None, "vol": None},
        ]

    @staticmethod
    def _empty_overview() -> dict:
        return {
            "indices": PriceService._default_indices(),
            "market_stats": {
                "up_count": 0, "down_count": 0, "flat_count": 0,
                "limit_up": 0, "limit_down": 0, "total_amount": None,
            },
            "updated_at": None,
        }

    def get_sectors(self, sector_type: str = "industry") -> dict:
        """获取板块涨跌幅（从轮动数据源获取）。"""
        try:
            ds = get_ds_manager()
            items = ds.get_sectors()
            if items:
                return {
                    "type": sector_type,
                    "items": items,
                    "updated_at": datetime.now(CN_TZ).isoformat(),
                }
        except Exception:
            logger.exception("获取板块数据失败")

        return {"type": sector_type, "items": [], "updated_at": None}


# ── 股本懒加载辅助函数 ──────────────────────────────


def _fetch_shares_sina(symbol: str, market: str) -> tuple[float | None, float | None]:
    """Sina 市场中心 → (总股本万股, 流通股本万股)。二分搜索定位。"""
    import json, requests
    headers = {"Referer": "https://finance.sina.com.cn"}
    url = (
        "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
        "Market_Center.getHQNodeData"
    )
    node = "sh_a" if market == "sh" else "sz_a"

    def _query_page(page: int) -> dict | None:
        try:
            r = requests.get(url,
                params={"page": page, "num": 80, "sort": "symbol", "asc": 1, "node": node},
                headers=headers, timeout=8)
            items = json.loads(r.text)
            if not items:
                return None
            for it in items:
                if str(it.get("code", "")) == symbol:
                    return it
            return {"_first": items[0].get("code", ""), "_last": items[-1].get("code", "")}
        except Exception:
            return None

    # 二分搜索，最多10次查询
    lo, hi = 1, 50
    while lo <= hi:
        mid = (lo + hi) // 2
        result = _query_page(mid)
        if result is None:
            return None, None
        if "mktcap" in result:  # 找到了
            mktcap = result.get("mktcap")
            nmc = result.get("nmc")
            trade = float(result.get("trade", 0))
            total = float(mktcap) if mktcap and trade > 0 else None
            fl = float(nmc) if nmc and trade > 0 else None
            if total and trade > 0:
                total = total / trade
            if fl and trade > 0:
                fl = fl / trade
            return total, fl
        first = result["_first"]
        last = result["_last"]
        if first <= symbol <= last:
            # 在当前页但没找到（可能不在本页的返回范围内）
            return None, None
        elif symbol < first:
            hi = mid - 1
        else:
            lo = mid + 1

    return None, None


def _fetch_shares_em(symbol: str) -> tuple[float | None, float | None]:
    """AKShare stock_individual_info_em。→ (总股本万股, 流通股万股)"""
    import akshare as ak
    df = ak.stock_individual_info_em(symbol=symbol)
    info = {}
    for _, row in df.iterrows():
        info[str(row["item"]).strip()] = str(row["value"]).strip()
    total = None
    fl = None
    if (cap := info.get("总股本")):
        try:
            total = float(cap.replace(",", "")) / 10000
        except (ValueError, TypeError):
            pass
    if (float_s := info.get("流通股")):
        try:
            fl = float(float_s.replace(",", "")) / 10000
        except (ValueError, TypeError):
            pass
    return total, fl


def _fetch_shares_cninfo(symbol: str) -> tuple[float | None, float | None]:
    """AKShare stock_profile_cninfo（备选）。"""
    import akshare as ak
    try:
        df = ak.stock_profile_cninfo(symbol=symbol)
        if df.empty:
            return None, None
        row = df.iloc[0]
        cols = list(df.columns)
        total = None
        fl = None
        for c in cols:
            val = row.get(c) if hasattr(row, "get") else row[c]
            if val and not total and "总股本" in str(c):
                try:
                    total = float(str(val).replace(",", "")) / 10000
                except (ValueError, TypeError):
                    pass
            if val and not fl and "流通" in str(c) and "限售" not in str(c):
                try:
                    fl = float(str(val).replace(",", "")) / 10000
                except (ValueError, TypeError):
                    pass
        return total, fl
    except Exception:
        return None, None
