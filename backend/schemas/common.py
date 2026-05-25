"""统一响应与分页模型。"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = Field(default=0, description="0=成功, 非0=业务错误")
    message: str = Field(default="ok")
    data: T | None = None
    ts: int = Field(description="服务器时间戳（毫秒）")


class PaginationMeta(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int


class PaginatedData(BaseModel, Generic[T]):
    list: list[T]
    pagination: PaginationMeta
