"""财务数据、公告、新闻、自选股、告警规则业务逻辑。"""

import logging
from datetime import date, datetime

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from models.announcement import Announcement
from models.daily_price import DailyPrice
from models.financial import Financial
from models.news import News
from models.stock import Stock
from models.watchlist import AlertRule, Watchlist

logger = logging.getLogger(__name__)


class FinancialService:
    """财务数据查询服务。"""

    def __init__(self, db: Session):
        self.db = db

    def get_financials(
        self,
        ts_code: str,
        report_type: str = "Q",
        limit: int = 12,
    ) -> dict | None:
        """获取财务数据列表。"""
        query = (
            self.db.query(Financial)
            .filter(Financial.ts_code == ts_code)
        )
        if report_type:
            query = query.filter(Financial.report_type == report_type)

        rows = (
            query.order_by(Financial.period.desc())
            .limit(limit)
            .all()
        )

        items = []
        for r in rows:
            items.append({
                "period": r.period,
                "report_type": r.report_type,
                "revenue": float(r.revenue) if r.revenue else None,
                "net_profit": float(r.net_profit) if r.net_profit else None,
                "gross_margin": float(r.gross_margin) if r.gross_margin else None,
                "net_margin": float(r.net_margin) if r.net_margin else None,
                "total_assets": float(r.total_assets) if r.total_assets else None,
                "total_debt": float(r.total_debt) if r.total_debt else None,
                "equity": float(r.equity) if r.equity else None,
                "debt_ratio": float(r.debt_ratio) if r.debt_ratio else None,
                "cfo": float(r.cfo) if r.cfo else None,
                "roe": float(r.roe) if r.roe else None,
                "eps": float(r.eps) if r.eps else None,
                "bvps": float(r.bvps) if r.bvps else None,
            })

        return {
            "ts_code": ts_code,
            "items": items,
        }


class AnnouncementService:
    """公告查询服务。"""

    def __init__(self, db: Session):
        self.db = db

    def search(
        self,
        ts_code: str,
        ann_type: str | None = None,
        start_date: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """查询公告列表。"""
        query = self.db.query(Announcement).filter(Announcement.ts_code == ts_code)

        if ann_type:
            query = query.filter(Announcement.ann_type == ann_type)
        if start_date:
            query = query.filter(Announcement.pub_date >= date.fromisoformat(start_date))

        total = query.count()
        rows = (
            query.order_by(Announcement.pub_date.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        items = [
            {
                "id": r.id,
                "ts_code": r.ts_code,
                "title": r.title,
                "ann_type": r.ann_type,
                "pub_date": r.pub_date,
                "url": r.url,
                "summary": r.summary,
            }
            for r in rows
        ]

        return items, total


class NewsService:
    """新闻查询服务。"""

    def __init__(self, db: Session):
        self.db = db

    def search(
        self,
        ts_code: str | None = None,
        source: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """查询新闻列表。"""
        query = self.db.query(News)

        if ts_code:
            query = query.filter(News.related_codes.contains(ts_code))
        if source:
            query = query.filter(News.source == source)

        total = query.count()
        rows = (
            query.order_by(News.pub_time.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        items = []
        for r in rows:
            related_codes = None
            if r.related_codes:
                related_codes = [c.strip() for c in r.related_codes.split(",") if c.strip()]

            items.append({
                "id": r.id,
                "source": r.source,
                "title": r.title,
                "url": r.url,
                "pub_time": r.pub_time.isoformat() if r.pub_time else None,
                "related_codes": related_codes,
                "sentiment": float(r.sentiment) if r.sentiment else None,
                "summary": r.summary,
                "impact_sectors": r.impact_sectors,
                "impact_level": r.impact_level,
                "is_breaking": r.is_breaking,
            })

        return items, total


class WatchlistService:
    """自选股业务逻辑。"""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _normalize_code(ts_code: str) -> str:
        """补全股票代码的市场后缀。"""
        ts_code = ts_code.strip().upper()
        if "." in ts_code:
            return ts_code
        if len(ts_code) == 6:
            if ts_code.startswith("6"):
                return f"{ts_code}.SH"
            elif ts_code.startswith("0") or ts_code.startswith("3"):
                return f"{ts_code}.SZ"
            elif ts_code.startswith("8") or ts_code.startswith("4"):
                return f"{ts_code}.BJ"
        return ts_code

    def get_all(self) -> dict:
        """获取所有自选股，按分组聚合，含最新行情。

        行情优先级：数据库日行情 → 轮动数据源实时行情 → null
        """
        items = self.db.query(Watchlist).order_by(Watchlist.created_at.desc()).all()
        if not items:
            return {"groups": []}

        # 批量查股票名
        codes = {w.ts_code for w in items}
        stocks_map = {
            s.ts_code: s
            for s in self.db.query(Stock).filter(Stock.ts_code.in_(codes)).all()
        }

        # 批量查最新日行情
        from sqlalchemy import and_
        sub = (
            self.db.query(
                DailyPrice.ts_code,
                func.max(DailyPrice.trade_date).label("max_date"),
            )
            .filter(DailyPrice.ts_code.in_(codes))
            .group_by(DailyPrice.ts_code)
            .subquery()
        )
        prices = (
            self.db.query(DailyPrice)
            .join(sub, and_(
                DailyPrice.ts_code == sub.c.ts_code,
                DailyPrice.trade_date == sub.c.max_date,
            ))
            .all()
        )
        price_map = {p.ts_code: p for p in prices}

        # 对 DB 无行情的股票，尝试轮动数据源获取实时行情
        missing = [c for c in codes if c not in price_map]
        ds_quotes: dict[str, dict] = {}
        if missing:
            try:
                from datasources.manager import get_ds_manager
                ds = get_ds_manager()
                for mc in missing:
                    q = ds.get_stock_quote(mc)
                    if q:
                        ds_quotes[mc] = {
                            "price": q.price,
                            "pct_chg": q.pct_chg,
                            "change": q.change,
                            "vol": q.vol,
                            "pre_close": q.pre_close,
                        }
            except Exception:
                pass

        # 按分组归类
        groups: dict[str, list[dict]] = {}
        for w in items:
            group_name = w.group_name or "默认"
            if group_name not in groups:
                groups[group_name] = []

            dp = price_map.get(w.ts_code)
            ds_q = ds_quotes.get(w.ts_code)
            stock = stocks_map.get(w.ts_code)

            if dp:
                price = float(dp.close) if dp.close else None
                pre_close = float(dp.pre_close) if dp.pre_close else None
                pct_chg = float(dp.pct_chg) if dp.pct_chg else None
                vol = float(dp.vol) if dp.vol else None
            elif ds_q:
                price = ds_q["price"]
                pre_close = ds_q["pre_close"]
                pct_chg = ds_q["pct_chg"]
                vol = ds_q["vol"]
            else:
                price = pre_close = pct_chg = vol = None

            change = round(price - pre_close, 3) if price and pre_close else None
            cost = float(w.cost_price) if w.cost_price else None
            pnl_pct = round((price - cost) / cost * 100, 2) if price and cost and cost > 0 else None

            groups[group_name].append({
                "id": w.id,
                "ts_code": w.ts_code,
                "name": stock.name if stock else w.ts_code,
                "price": price,
                "pct_chg": pct_chg,
                "change": change,
                "vol": vol,
                "cost_price": cost,
                "pnl_pct": pnl_pct,
                "note": w.note,
                "added_at": w.created_at,
            })

        return {
            "groups": [
                {"group_name": name, "stocks": stocks}
                for name, stocks in groups.items()
            ],
        }

    def add(self, ts_code: str, group_name: str = "默认", note: str | None = None, cost_price: float | None = None) -> dict:
        """添加自选股，重复则更新。自动补全市场后缀。"""
        ts_code = self._normalize_code(ts_code)
        existing = (
            self.db.query(Watchlist)
            .filter(Watchlist.ts_code == ts_code, Watchlist.group_name == group_name)
            .first()
        )
        if existing:
            if note is not None:
                existing.note = note
            if cost_price is not None:
                existing.cost_price = cost_price
            self.db.commit()
            self.db.refresh(existing)
            w = existing
        else:
            w = Watchlist(
                ts_code=ts_code,
                group_name=group_name,
                note=note,
                cost_price=cost_price,
            )
            self.db.add(w)
            self.db.commit()
            self.db.refresh(w)
        return {
            "id": w.id,
            "ts_code": w.ts_code,
            "group_name": w.group_name,
            "created_at": w.created_at,
        }

    def update(self, item_id: int, data: dict) -> dict | None:
        """更新自选股（仅更新传入字段）。"""
        w = self.db.query(Watchlist).filter(Watchlist.id == item_id).first()
        if not w:
            return None

        if "group_name" in data and data["group_name"] is not None:
            w.group_name = data["group_name"]
        if "note" in data:
            w.note = data["note"]
        if "cost_price" in data:
            w.cost_price = data["cost_price"]

        self.db.commit()
        self.db.refresh(w)
        return {
            "id": w.id,
            "ts_code": w.ts_code,
            "group_name": w.group_name,
            "created_at": w.created_at,
        }

    def delete(self, item_id: int) -> bool:
        """删除自选股。"""
        w = self.db.query(Watchlist).filter(Watchlist.id == item_id).first()
        if not w:
            return False
        self.db.delete(w)
        self.db.commit()
        return True


class AlertService:
    """告警规则业务逻辑。"""

    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> list[dict]:
        """获取所有告警规则。"""
        rows = self.db.query(AlertRule).order_by(AlertRule.created_at.desc()).all()
        result = []
        for r in rows:
            stock = self.db.query(Stock).filter(Stock.ts_code == r.ts_code).first()
            result.append({
                "id": r.id,
                "ts_code": r.ts_code,
                "stock_name": stock.name if stock else None,
                "rule_type": r.rule_type,
                "threshold": float(r.threshold),
                "direction": r.direction,
                "channel": r.channel,
                "channel_cfg": r.channel_cfg,
                "is_active": r.is_active,
                "last_triggered": r.last_triggered.isoformat() if r.last_triggered else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })
        return result

    def create(self, data: dict) -> dict:
        """创建告警规则。"""
        rule = AlertRule(
            ts_code=data["ts_code"],
            rule_type=data["rule_type"],
            threshold=data["threshold"],
            direction=data["direction"],
            channel=data["channel"],
            channel_cfg=data.get("channel_cfg", {}),
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)

        stock = self.db.query(Stock).filter(Stock.ts_code == rule.ts_code).first()
        return {
            "id": rule.id,
            "ts_code": rule.ts_code,
            "stock_name": stock.name if stock else None,
            "rule_type": rule.rule_type,
            "threshold": float(rule.threshold),
            "direction": rule.direction,
            "channel": rule.channel,
            "channel_cfg": rule.channel_cfg,
            "is_active": rule.is_active,
            "last_triggered": None,
            "created_at": rule.created_at.isoformat() if rule.created_at else None,
        }

    def update(self, alert_id: int, data: dict) -> dict | None:
        """更新告警规则。"""
        rule = self.db.query(AlertRule).filter(AlertRule.id == alert_id).first()
        if not rule:
            return None

        for key in ("threshold", "is_active", "direction", "channel_cfg"):
            if key in data and data[key] is not None:
                setattr(rule, key, data[key])

        self.db.commit()
        self.db.refresh(rule)
        return self._to_dict(rule)

    def delete(self, alert_id: int) -> bool:
        """删除告警规则。"""
        rule = self.db.query(AlertRule).filter(AlertRule.id == alert_id).first()
        if not rule:
            return False
        self.db.delete(rule)
        self.db.commit()
        return True

    def _to_dict(self, rule: AlertRule) -> dict:
        stock = self.db.query(Stock).filter(Stock.ts_code == rule.ts_code).first()
        return {
            "id": rule.id,
            "ts_code": rule.ts_code,
            "stock_name": stock.name if stock else None,
            "rule_type": rule.rule_type,
            "threshold": float(rule.threshold),
            "direction": rule.direction,
            "channel": rule.channel,
            "channel_cfg": rule.channel_cfg,
            "is_active": rule.is_active,
            "last_triggered": rule.last_triggered.isoformat() if rule.last_triggered else None,
            "created_at": rule.created_at.isoformat() if rule.created_at else None,
        }
