"""系统状态路由。"""

import time

from fastapi import APIRouter
from sqlalchemy import text

from cache import get_cache
from config import get_settings
from database import SessionLocal
from schemas.common import ApiResponse
from schemas.system import JobInfo, SchedulerStatus, SystemStatus, TriggerResult
from scheduler import scheduler

router = APIRouter(prefix="/system", tags=["system"])
settings = get_settings()
cache = get_cache()


@router.get("/status", response_model=ApiResponse[SystemStatus])
def get_status():
    """服务状态。"""
    # 数据库状态
    db_status = "ok"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception:
        db_status = "error"

    # Redis 状态
    redis_status = "ok"
    if settings.REDIS_URL:
        try:
            cached = cache.get("__health_check__")
            if cached is None:
                cache.set("__health_check__", "ok", 10)
        except Exception:
            redis_status = "unavailable"
    else:
        redis_status = "unavailable"

    # 调度器状态
    scheduler_running = scheduler.running if hasattr(scheduler, "running") else False
    jobs = []
    if scheduler_running:
        for job in scheduler.get_jobs():
            jobs.append(JobInfo(
                id=job.id,
                name=job.name,
                next_run=job.next_run_time.isoformat() if job.next_run_time else None,
                last_run=None,
                last_status=None,
                last_count=None,
            ))

    return ApiResponse(
        data=SystemStatus(
            api="ok",
            database=db_status,
            redis=redis_status,
            scheduler=SchedulerStatus(running=scheduler_running, jobs=jobs),
        ),
        ts=int(time.time() * 1000),
    )


@router.post("/trigger/{job_id}", response_model=ApiResponse[TriggerResult])
def trigger_job(job_id: str):
    """手动触发采集任务。"""
    if not hasattr(scheduler, "running") or not scheduler.running:
        return ApiResponse(
            code=1003,
            message="调度器未启动",
            data=TriggerResult(job_id=job_id, triggered=False, message="调度器未启动"),
            ts=int(time.time() * 1000),
        )

    try:
        job = scheduler.get_job(job_id)
        if job is None:
            return ApiResponse(
                code=1002,
                message=f"任务不存在: {job_id}",
                data=TriggerResult(job_id=job_id, triggered=False, message=f"未找到任务: {job_id}"),
                ts=int(time.time() * 1000),
            )
        # 立即执行任务（不等待）
        job.modify(next_run_time=None)  # 触发立即执行
        return ApiResponse(
            data=TriggerResult(job_id=job_id, triggered=True, message="任务已加入执行队列"),
            ts=int(time.time() * 1000),
        )
    except Exception as e:
        return ApiResponse(
            code=5001,
            message=f"触发失败: {e}",
            data=TriggerResult(job_id=job_id, triggered=False, message=str(e)),
            ts=int(time.time() * 1000),
        )
