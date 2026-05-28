"""SQLAlchemy 引擎、会话工厂、UPSERT 工具、以及依赖注入辅助。"""

import logging
from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# SQLite 需要 check_same_thread=False
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖注入：获取数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """创建所有表（开发用，生产用 alembic）。"""
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表初始化完成")


def is_postgresql(db: Session) -> bool:
    """判断当前是否为 PostgreSQL 数据库。"""
    return "postgresql" in str(db.bind.url)


def upsert_records(
    db: Session,
    model: type[Base],
    records: list[dict],
    index_elements: list[str],
    update_cols: list[str] | None = None,
):
    """通用 UPSERT：PostgreSQL 用 ON CONFLICT，SQLite 用 INSERT OR REPLACE。

    Args:
        db: 数据库会话
        model: ORM 模型类
        records: 待写入的字典列表
        index_elements: 唯一约束列名列表
        update_cols: 冲突时更新的列（None=全部更新）
    """
    if not records:
        return

    if is_postgresql(db):
        # PostgreSQL: INSERT ... ON CONFLICT DO UPDATE
        stmt = pg_insert(model).values(records)
        if update_cols is None:
            update_cols = [
                c.key for c in inspect(model).columns
                if c.key not in index_elements and not c.primary_key and c.key != "id"
            ]
        set_vals = {col: getattr(stmt.excluded, col) for col in update_cols}
        stmt = stmt.on_conflict_do_update(index_elements=index_elements, set_=set_vals)
        db.execute(stmt)
    else:
        # SQLite: 逐行 INSERT OR REPLACE（SQLite 不支持原生 ON CONFLICT DO UPDATE）
        columns = [
            c.key for c in inspect(model).columns
            if not (c.primary_key and c.autoincrement)
        ]
        col_names = ", ".join(columns)
        placeholders = ", ".join([f":{c}" for c in columns])
        sql = text(f"INSERT OR REPLACE INTO {model.__tablename__} ({col_names}) VALUES ({placeholders})")

        for record in records:
            params = {}
            for c in columns:
                val = record.get(c)
                params[c] = str(val) if isinstance(val, (str,)) and not isinstance(val, str) else val
            db.execute(sql, record)

    db.commit()
