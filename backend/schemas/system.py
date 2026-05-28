"""系统状态 schemas。"""

from datetime import datetime

from pydantic import BaseModel


class JobInfo(BaseModel):
    id: str
    name: str
    next_run: datetime | None = None
    last_run: datetime | None = None
    last_status: str | None = None
    last_count: int | None = None


class SchedulerStatus(BaseModel):
    running: bool
    jobs: list[JobInfo]


class SystemStatus(BaseModel):
    api: str = "ok"
    database: str = "ok"
    redis: str = "ok"
    scheduler: SchedulerStatus


class TriggerResult(BaseModel):
    job_id: str
    triggered: bool
    message: str
