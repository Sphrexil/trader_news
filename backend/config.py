"""应用配置模块。

环境变量读取优先级：系统环境变量 > .env 文件 > 默认值。
"""

import os
from functools import lru_cache
from pathlib import Path

# 加载 .env 文件（如果存在）
try:
    from dotenv import load_dotenv

    _env_file = Path(__file__).resolve().parent / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
except ImportError:
    pass


class Settings:
    PROJECT_NAME: str = "a-stock-info"
    VERSION: str = "2.0.0"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # 数据库
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./dev.db",
    )

    # Redis（可选，不填则降级为内存缓存）
    REDIS_URL: str | None = os.getenv("REDIS_URL")

    # 密钥
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    # 采集器配置
    CRAWLER_RETRY_TIMES: int = 3
    CRAWLER_RETRY_BASE_DELAY: float = 1.0
    CRAWLER_POLITE_DELAY: float = 0.1

    # 交易时间（北京时间）
    TRADING_START: str = "09:30"
    TRADING_END: str = "15:00"

    # 告警推送
    BARK_DEFAULT_KEY: str | None = os.getenv("BARK_DEFAULT_KEY")
    SMTP_HOST: str | None = os.getenv("SMTP_HOST")
    SMTP_USER: str | None = os.getenv("SMTP_USER")
    SMTP_PASS: str | None = os.getenv("SMTP_PASS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
