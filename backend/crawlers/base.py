"""采集器基类。

提供统一日志、异常捕获+重试、UPSERT 写入封装、采集结果统计上报。
"""

import logging
import time
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from database import SessionLocal, upsert_records

logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    """所有采集器继承此类。

    子类只需实现 fetch()，基类处理重试、写入、统计。
    """

    # 子类覆写
    model: type | None = None
    index_elements: list[str] = []
    update_cols: list[str] | None = None

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay

    @abstractmethod
    def fetch(self, db: Session) -> list[dict]:
        """子类实现：拉取原始数据，返回标准化字典列表。"""
        ...

    def upsert(self, db: Session, records: list[dict]):
        """写入数据库（UPSERT）。"""
        if not self.model or not self.index_elements:
            logger.warning("%s: model/index_elements 未配置，跳过写入", self.__class__.__name__)
            return
        upsert_records(db, self.model, records, self.index_elements, self.update_cols)

    def on_success(self, count: int):
        """采集成功后的回调（子类可覆写，用于缓存失效等）。"""
        pass

    def run(self) -> int:
        """执行采集，带重试逻辑。返回写入条数。"""
        db = SessionLocal()
        try:
            for attempt in range(self.max_retries):
                try:
                    records = self.fetch(db)
                    self.upsert(db, records)
                    logger.info("%s 完成，写入 %d 条", self.__class__.__name__, len(records))
                    self.on_success(len(records))
                    return len(records)
                except Exception as e:
                    db.rollback()
                    wait = self.base_delay * (2**attempt)
                    logger.warning(
                        "%s 第%d次失败：%s，%ss后重试",
                        self.__class__.__name__, attempt + 1, e, wait,
                    )
                    time.sleep(wait)
            logger.error("%s 最终失败", self.__class__.__name__)
            return -1
        finally:
            db.close()
