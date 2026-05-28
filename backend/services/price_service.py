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
        """
        stock = self.db.query(Stock).filter(Stock.ts_code == ts_code).first()
        if not stock:
            return None

        # 尝试从 Redis 读取实时行情
        rt_key = f"rt:quote:{ts_code}"
        cached = cache.get(rt_key)
        if cached:
            cached["is_trading"] = _is_trading_time()
            return cached

        # 降级：读数据库最新日行情
        dp = self.get_latest_daily_price(ts_code)

        # 二次降级：轮动数据源实时行情
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
            "is_trading": _is_trading_time(),
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

        DB优先，轮动数据源补充缺失日期 → 合并去重。
        """
        if period != "daily":
            period = "daily"

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

        for r in query.all():
            d = str(r.trade_date) if hasattr(r.trade_date, "isoformat") else str(r.trade_date)
            dates_seen.add(d)
            items.append({
                "date": r.trade_date,
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

        # 排序，取最近 limit 条
        items.sort(key=lambda x: str(x["date"]))
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
                return self._empty_overview()

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
