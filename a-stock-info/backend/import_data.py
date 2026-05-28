"""数据导入脚本 — 首次启动时运行，从 AKShare 导入基础数据。

用法:
    cd backend
    python import_data.py              # 导入全部(股票列表 + 50只行情 + 新闻)
    python import_data.py --stocks-only # 仅股票列表
    python import_data.py --price-count 100  # 导入100只股票的行情
"""

import argparse
import logging
import sys
import time

# 日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("import_data")

# 确保当前目录在 sys.path
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, SessionLocal
from cache import get_cache


def import_stock_list():
    """导入全量 A 股股票列表。"""
    logger.info("=" * 50)
    logger.info("Step 1: 导入股票列表...")
    try:
        import akshare as ak

        df = ak.stock_info_a_code_name()
        logger.info(f"AKShare 返回 {len(df)} 条记录")

        db = SessionLocal()
        inserted = 0
        for _, row in df.iterrows():
            code = str(row.get("code", ""))
            name = str(row.get("name", ""))
            if not code:
                continue

            # 根据代码前两位判断市场
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

            # UPSERT
            from sqlalchemy import text
            db.execute(
                text(
                    "INSERT OR REPLACE INTO stocks (ts_code, name, market, industry) "
                    "VALUES (:ts_code, :name, :market, :industry)"
                ),
                {"ts_code": ts_code, "name": name, "market": market, "industry": None},
            )
            inserted += 1
            if inserted % 500 == 0:
                db.commit()
                logger.info(f"  已导入 {inserted} 只股票...")

        db.commit()
        logger.info(f"股票列表导入完成: {inserted} 只")
        db.close()
        return inserted
    except ImportError:
        logger.error("akshare 未安装，请先 pip install akshare")
        return 0
    except Exception as e:
        logger.error(f"导入股票列表失败: {e}")
        return 0


def import_daily_prices(limit: int = 50):
    """导入部分股票的当日行情。"""
    logger.info("=" * 50)
    logger.info(f"Step 2: 导入日行情 (前 {limit} 只)...")

    try:
        import akshare as ak
        from datetime import date

        db = SessionLocal()

        # 获取股票列表
        from sqlalchemy import text
        rows = db.execute(text("SELECT ts_code FROM stocks LIMIT :limit"), {"limit": limit}).fetchall()
        codes = [r[0] for r in rows]

        if not codes:
            logger.warning("股票列表为空，请先运行 import_stock_list()")
            db.close()
            return 0

        today = date.today().isoformat()
        inserted = 0

        for ts_code in codes:
            symbol = ts_code.split(".")[0]
            try:
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=today,
                    end_date=today,
                    adjust="qfq",
                )
                if df.empty:
                    continue

                row = df.iloc[-1]
                db.execute(
                    text(
                        "INSERT OR REPLACE INTO daily_prices "
                        "(ts_code, trade_date, open, high, low, close, pre_close, "
                        "pct_chg, vol, amount, turnover_rate, total_mv, circ_mv) "
                        "VALUES (:1,:2,:3,:4,:5,:6,:7,:8,:9,:10,:11,:12,:13)"
                    ),
                    {
                        "1": ts_code, "2": today,
                        "3": float(row["开盘"]) if row.get("开盘") else None,
                        "4": float(row["最高"]) if row.get("最高") else None,
                        "5": float(row["最低"]) if row.get("最低") else None,
                        "6": float(row["收盘"]) if row.get("收盘") else None,
                        "7": float(row["昨收"]) if row.get("昨收") else None,
                        "8": float(row["涨跌幅"]) if row.get("涨跌幅") else None,
                        "9": float(row["成交量"]) if row.get("成交量") else None,
                        "10": float(row["成交额"]) if row.get("成交额") else None,
                        "11": float(row["换手率"]) if row.get("换手率") else None,
                        "12": None, "13": None,
                    },
                )
                inserted += 1
                if inserted % 20 == 0:
                    db.commit()
                    logger.info(f"  已导入 {inserted} 条行情...")

                time.sleep(0.05)  # 礼貌延迟
            except Exception as e:
                logger.debug(f"  {ts_code} 失败: {e}")
                continue

        db.commit()
        logger.info(f"日行情导入完成: {inserted} 条")
        db.close()
        return inserted
    except ImportError:
        logger.error("akshare 未安装")
        return 0
    except Exception as e:
        logger.error(f"导入行情失败: {e}")
        return 0


def import_news():
    """导入最新财经新闻。"""
    logger.info("=" * 50)
    logger.info("Step 3: 导入财经新闻...")

    try:
        import akshare as ak
        from datetime import datetime

        df = ak.stock_news_em()
        if df.empty:
            logger.warning("无新闻数据")
            return 0

        db = SessionLocal()
        inserted = 0
        from sqlalchemy import text

        for _, row in df.head(100).iterrows():
            url = str(row.get("新闻链接", ""))
            if not url:
                continue

            try:
                db.execute(
                    text(
                        "INSERT OR IGNORE INTO news (source, title, url, pub_time, related_codes, sentiment) "
                        "VALUES (:source, :title, :url, :pub_time, :related_codes, :sentiment)"
                    ),
                    {
                        "source": str(row.get("文章来源", "东方财富")),
                        "title": str(row.get("标题", "")),
                        "url": url,
                        "pub_time": datetime.now().isoformat(),
                        "related_codes": str(row.get("股票代码", "")) if row.get("股票代码") else None,
                        "sentiment": None,
                    },
                )
                inserted += 1
            except Exception:
                continue

        db.commit()
        logger.info(f"新闻导入完成: {inserted} 条")
        db.close()
        return inserted
    except ImportError:
        logger.error("akshare 未安装")
        return 0
    except Exception as e:
        logger.error(f"导入新闻失败: {e}")
        return 0


def main():
    parser = argparse.ArgumentParser(description="数据导入工具")
    parser.add_argument("--stocks-only", action="store_true", help="仅导入股票列表")
    parser.add_argument("--price-count", type=int, default=50, help="导入行情的股票数量")
    parser.add_argument("--skip-news", action="store_true", help="跳过新闻导入")
    args = parser.parse_args()

    logger.info("数据导入开始")
    init_db()

    # Step 1: 股票列表
    n_stocks = import_stock_list()

    if args.stocks_only:
        logger.info(f"完成! 导入 {n_stocks} 只股票")
        return

    # Step 2: 行情
    if n_stocks > 0:
        n_prices = import_daily_prices(limit=args.price_count)
    else:
        n_prices = 0

    # Step 3: 新闻
    if not args.skip_news:
        n_news = import_news()
    else:
        n_news = 0

    logger.info("=" * 50)
    logger.info(f"导入完成! 股票:{n_stocks} 行情:{n_prices} 新闻:{n_news}")

    # 清除相关缓存
    cache = get_cache()
    cache.delete("market:overview")
    cache.delete_pattern("market:sectors:*")


if __name__ == "__main__":
    main()
