"""统一缓存抽象层。

Redis 可用时使用 Redis，否则降级为内存字典。
业务代码只调用 get/set/delete，不感知底层实现。
"""

from __future__ import annotations

import json
import time
from typing import Any

import redis

from config import get_settings

settings = get_settings()


class _MemoryStore:
    """进程内内存缓存（Redis 不可用时的降级方案）。"""

    def __init__(self):
        self._store: dict[str, tuple[Any, float | None]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expire_at = entry
        if expire_at and time.time() > expire_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int | None = None):
        expire_at = time.time() + ttl if ttl else None
        self._store[key] = (value, expire_at)

    def delete(self, key: str):
        self._store.pop(key, None)

    def delete_pattern(self, pattern: str):
        # 简易通配符匹配（仅支持 * 在末尾）
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            keys = [k for k in self._store if k.startswith(prefix)]
            for k in keys:
                del self._store[k]
        else:
            self._store.pop(pattern, None)


class Cache:
    def __init__(self):
        self._redis = None
        self._memory = _MemoryStore()
        if settings.REDIS_URL:
            try:
                self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
                self._redis.ping()
            except Exception:
                self._redis = None

    def get(self, key: str) -> Any | None:
        if self._redis:
            try:
                raw = self._redis.get(key)
                if raw is None:
                    return None
                value = json.loads(raw)
                if value is None:
                    self._redis.delete(key)
                return value
            except Exception:
                pass
        value = self._memory.get(key)
        return value

    def set(self, key: str, value: Any, ttl: int | None = None):
        if value is None:
            self.delete(key)
            return
        if self._redis:
            try:
                raw = json.dumps(value, ensure_ascii=False, default=str)
                if raw == "null":
                    self.delete(key)
                    return
                self._redis.set(key, raw, ex=ttl)
                return
            except Exception:
                pass
        self._memory.set(key, value, ttl)

    def delete(self, key: str):
        if self._redis:
            try:
                self._redis.delete(key)
                return
            except Exception:
                pass
        self._memory.delete(key)

    def delete_pattern(self, pattern: str):
        if self._redis:
            try:
                keys = self._redis.keys(pattern)
                if keys:
                    self._redis.delete(*keys)
                return
            except Exception:
                pass
        self._memory.delete_pattern(pattern)


_cache: Cache | None = None


def get_cache() -> Cache:
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache
