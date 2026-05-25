"""股票基础信息业务逻辑。"""

import logging

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from models.daily_price import DailyPrice
from models.stock import Stock

logger = logging.getLogger(__name__)


class StockService:
    """股票查询服务。"""

    def __init__(self, db: Session):
        self.db = db

    def search(
        self,
        q: str | None = None,
        market: str | None = None,
        industry: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """模糊搜索股票，支持代码/名称/拼音首字母，返回列表+总数。"""
        # 基查询：仅在市股票
        query = self.db.query(Stock).filter(Stock.delist_date.is_(None))

        # 模糊搜索
        if q:
            like_q = f"%{q}%"
            query = query.filter(
                or_(
                    Stock.ts_code.ilike(like_q),
                    Stock.name.ilike(like_q),
                )
            )

        # 市场筛选
        if market:
            query = query.filter(Stock.market == market.upper())

        # 行业筛选
        if industry:
            query = query.filter(Stock.industry == industry)

        # 总数
        total = query.count()

        # 分页
        stocks = (
            query.order_by(Stock.ts_code)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        # 获取每个股票的最新行情数据（最新 total_mv, circ_mv, pct_chg）
        stock_codes = [s.ts_code for s in stocks]
        latest_prices = {}
        if stock_codes:
            sub = (
                self.db.query(
                    DailyPrice.ts_code,
                    func.max(DailyPrice.trade_date).label("max_date"),
                )
                .filter(DailyPrice.ts_code.in_(stock_codes))
                .group_by(DailyPrice.ts_code)
                .subquery()
            )
            prices = (
                self.db.query(DailyPrice)
                .join(
                    sub,
                    (DailyPrice.ts_code == sub.c.ts_code)
                    & (DailyPrice.trade_date == sub.c.max_date),
                )
                .all()
            )
            latest_prices = {p.ts_code: p for p in prices}

        # 构建返回
        result = []
        for s in stocks:
            p = latest_prices.get(s.ts_code)
            result.append({
                "ts_code": s.ts_code,
                "name": s.name,
                "market": s.market,
                "industry": s.industry,
                "list_date": s.list_date,
                "total_mv": float(p.total_mv) if p and p.total_mv else None,
                "circ_mv": float(p.circ_mv) if p and p.circ_mv else None,
                "pct_chg": float(p.pct_chg) if p and p.pct_chg else None,
            })

        return result, total

    def get_info(self, ts_code: str) -> dict | None:
        """获取个股基础信息。"""
        stock = (
            self.db.query(Stock)
            .filter(Stock.ts_code == ts_code)
            .first()
        )
        if not stock:
            return None

        return {
            "ts_code": stock.ts_code,
            "name": stock.name,
            "market": stock.market,
            "industry": stock.industry,
            "list_date": stock.list_date,
            "total_share": float(stock.total_share) if stock.total_share else None,
            "float_share": float(stock.float_share) if stock.float_share else None,
            "is_listed": stock.delist_date is None,
        }
