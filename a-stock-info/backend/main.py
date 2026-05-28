"""FastAPI 应用入口。"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import init_db
from routers import alerts, market, news, predict, stocks, stocks_extra, system, watchlist
from scheduler import shutdown_scheduler, start_scheduler

# 日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期。"""
    logger.info("启动中...")
    init_db()
    if not settings.DEBUG:
        start_scheduler()

    # 后台预热 Kronos 模型（不阻塞启动）
    try:
        import threading
        def _warmup():
            try:
                from predictors.kronos_predictor import get_kronos_predictor
                get_kronos_predictor()._ensure_loaded()
                logger.info("Kronos 模型预热完成")
            except Exception as e:
                logger.warning(f"Kronos 预热跳过: {e}")
        threading.Thread(target=_warmup, daemon=True).start()
    except Exception:
        pass
    yield
    if not settings.DEBUG:
        shutdown_scheduler()
    logger.info("已关闭")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 时间戳中间件
@app.middleware("http")
async def add_ts_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Server-Ts"] = str(int(time.time() * 1000))
    return response


# 注册路由
api_prefix = settings.API_PREFIX
app.include_router(stocks.router, prefix=api_prefix)
app.include_router(stocks_extra.router, prefix=api_prefix)
app.include_router(market.router, prefix=api_prefix)
app.include_router(news.router, prefix=api_prefix)
app.include_router(predict.router, prefix=api_prefix)
app.include_router(watchlist.router, prefix=api_prefix)
app.include_router(alerts.router, prefix=api_prefix)
app.include_router(system.router, prefix=api_prefix)


@app.get("/")
def root():
    return {"service": settings.PROJECT_NAME, "version": settings.VERSION}


@app.get("/health")
def health():
    return {"status": "ok"}
