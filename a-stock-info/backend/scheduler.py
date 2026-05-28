"""APScheduler 任务注册。"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="Asia/Shanghai")


def register_jobs():
    """注册所有采集定时任务。"""
    from crawlers.announcement import AnnouncementCrawler
    from crawlers.daily_price import DailyPriceCrawler
    from crawlers.financial import FinancialCrawler
    from crawlers.news import NewsCrawler
    from crawlers.stock_list import StockListCrawler

    # 全量股票元数据 — 每周一 09:00
    scheduler.add_job(
        StockListCrawler().run,
        trigger="cron",
        day_of_week="mon",
        hour=9,
        minute=0,
        id="sync_stock_list",
        name="股票列表同步",
    )

    # 日行情 — 工作日 17:00
    scheduler.add_job(
        DailyPriceCrawler().run,
        trigger="cron",
        day_of_week="mon-fri",
        hour=17,
        minute=0,
        id="sync_daily_price",
        name="日行情采集",
    )

    # 财务数据 — 每周一 08:00
    scheduler.add_job(
        FinancialCrawler().run,
        trigger="cron",
        day_of_week="mon",
        hour=8,
        minute=0,
        id="sync_financials",
        name="财务数据采集",
    )

    # 公告 — 工作日 08:30 / 18:00
    scheduler.add_job(
        AnnouncementCrawler().run,
        trigger="cron",
        day_of_week="mon-fri",
        hour=8,
        minute=30,
        id="sync_announcements_morning",
        name="公告采集（早）",
    )
    scheduler.add_job(
        AnnouncementCrawler().run,
        trigger="cron",
        day_of_week="mon-fri",
        hour=18,
        minute=0,
        id="sync_announcements_evening",
        name="公告采集（晚）",
    )

    # 新闻 — 每30分钟
    scheduler.add_job(
        NewsCrawler().run,
        trigger="interval",
        minutes=30,
        id="sync_news",
        name="新闻采集",
    )

    logger.info("调度器任务注册完成: %d 个任务", len(scheduler.get_jobs()))


def start_scheduler():
    if not scheduler.running:
        register_jobs()
        scheduler.start()
        logger.info("调度器已启动")


def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("调度器已关闭")
