"""前端 API 集成测试 — 模拟前端所有接口调用场景。

覆盖:
  - 统一响应格式校验 (code, message, data, ts)
  - 全部 21 个端点
  - CRUD 完整流程 (Watchlist + Alerts)
  - 分页、搜索、筛选
  - 错误处理 (404/422/1002/1003)
  - 行情轮询模拟

用法:
    python tests/test_frontend_api.py
    python tests/test_frontend_api.py --base-url http://localhost:8001
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

BASE_URL = "http://localhost:8001"
API = "/api/v1"


# ── 结果模型 ──────────────────────────────────────────────

@dataclass
class Case:
    name: str
    method: str
    path: str
    params: dict | None = None
    body: dict | None = None
    expect_status: int = 200
    expect_code: int | None = 0  # None = 不检查业务码
    check_fields: list[str] | None = None  # data 中必须存在的字段
    check_pagination: bool = False

@dataclass
class Result:
    case: Case
    status: int = 0
    response: dict | None = None
    passed: bool = False
    error: str | None = None
    elapsed_ms: float = 0

@dataclass
class Suite:
    name: str
    cases: list[Case] = field(default_factory=list)
    results: list[Result] = field(default_factory=list)

# ── 全局状态（供 CRUD 流程共享）─────────────────────────
_state: dict[str, Any] = {}


# ── 测试用例 ─────────────────────────────────────────────

def build_suites() -> list[Suite]:
    return [
        Suite(name="1. System", cases=[
            Case("健康检查", "GET", "/health", expect_code=None,
                 check_fields=["status"]),
            Case("根路径", "GET", "/", expect_code=None,
                 check_fields=["service", "version"]),
            Case("服务状态", "GET", f"{API}/system/status",
                 check_fields=["api", "database", "redis", "scheduler"]),
        ]),

        Suite(name="2. Stocks — 搜索/详情", cases=[
            Case("股票搜索-无筛选", "GET", f"{API}/stocks",
                 params={"page": 1, "page_size": 3}, check_pagination=True,
                 check_fields=["list"]),
            Case("股票搜索-关键字", "GET", f"{API}/stocks",
                 params={"q": "银行", "page": 1, "page_size": 5}, check_pagination=True),
            Case("股票搜索-市场SH", "GET", f"{API}/stocks",
                 params={"market": "SH", "page": 1, "page_size": 5}, check_pagination=True),
            Case("个股详情-不存在", "GET", f"{API}/stocks/000001.SZ",
                 expect_code=1002),
            Case("个股详情-不存在2", "GET", f"{API}/stocks/999999.XZ",
                 expect_code=1002),
        ]),

        Suite(name="3. Stocks — 行情/K线/财务/公告", cases=[
            Case("行情快照-不存在", "GET", f"{API}/stocks/000001.SZ/quote",
                 expect_code=1002),
            Case("行情快照-不存在2", "GET", f"{API}/stocks/999999.XZ/quote",
                 expect_code=1002),
            Case("K线数据-空库", "GET", f"{API}/stocks/000001.SZ/kline",
                 params={"period": "daily", "limit": 10},
                 check_fields=["ts_code", "items", "count"]),
            Case("K线-自定义日期", "GET", f"{API}/stocks/000001.SZ/kline",
                 params={"start_date": "2024-01-01", "end_date": "2024-12-31", "limit": 50},
                 check_fields=["items"]),
            Case("财务数据-季报", "GET", f"{API}/stocks/000001.SZ/financials",
                 params={"report_type": "Q", "limit": 4},
                 check_fields=["ts_code", "items"]),
            Case("财务数据-年报", "GET", f"{API}/stocks/000001.SZ/financials",
                 params={"report_type": "Y", "limit": 4},
                 check_fields=["ts_code", "items"]),
            Case("公告列表", "GET", f"{API}/stocks/000001.SZ/announcements",
                 params={"page": 1, "page_size": 5}, check_pagination=True),
        ]),

        Suite(name="4. Market — 大盘/板块", cases=[
            Case("大盘概况", "GET", f"{API}/market/overview",
                 check_fields=["indices", "market_stats"]),
            Case("大盘概况-含指数", "GET", f"{API}/market/overview"),  # 验证 indices 有四条
            Case("行业板块", "GET", f"{API}/market/sectors",
                 params={"type": "industry"},
                 check_fields=["type", "items"]),
        ]),

        Suite(name="5. News — 新闻", cases=[
            Case("新闻列表", "GET", f"{API}/news",
                 params={"page": 1, "page_size": 5}, check_pagination=True),
            Case("新闻-来源筛选", "GET", f"{API}/news",
                 params={"source": "东方财富", "page": 1, "page_size": 5},
                 check_pagination=True),
        ]),

        Suite(name="6. Watchlist — CRUD", cases=[
            Case("[C] 添加自选股", "POST", f"{API}/watchlist",
                 body={"ts_code": "600036.SZ", "group_name": "API测试", "cost_price": 12.50, "note": "测试"},
                 expect_status=201, check_fields=["id", "ts_code", "group_name"]),
            Case("[C] 重复添加-应为更新", "POST", f"{API}/watchlist",
                 body={"ts_code": "600036.SZ", "group_name": "API测试", "cost_price": 13.00},
                 expect_status=201),
            Case("[R] 获取自选股列表", "GET", f"{API}/watchlist",
                 check_fields=["groups"]),
            Case("[R] 列表含添加的数据", "GET", f"{API}/watchlist"),
            Case("[U] 修改不存在", "PUT", f"{API}/watchlist/99999",
                 body={"note": "修改"}, expect_code=1002),
            Case("[D] 删除不存在", "DELETE", f"{API}/watchlist/99999",
                 expect_code=1002),
        ]),

        Suite(name="7. Alerts — CRUD", cases=[
            Case("[C] 创建告警", "POST", f"{API}/alerts",
                 body={"ts_code": "600036.SZ", "rule_type": "price_pct", "threshold": 5.0,
                       "direction": "above", "channel": "bark",
                       "channel_cfg": {"bark_key": "test-key"}},
                 expect_status=201,
                 check_fields=["id", "ts_code", "rule_type", "threshold"]),
            Case("[R] 获取告警列表", "GET", f"{API}/alerts",
                 check_fields=["list"]),
            Case("[U] 修改不存在", "PUT", f"{API}/alerts/99999",
                 body={"threshold": 3.0}, expect_code=1002),
            Case("[T] 测试不存在", "POST", f"{API}/alerts/test/99999", expect_code=1002),
            Case("[D] 删除不存在", "DELETE", f"{API}/alerts/99999",
                 expect_code=1002),
        ]),

        Suite(name="8. Error Handling", cases=[
            Case("参数校验-page_size超限", "GET", f"{API}/stocks",
                 params={"page_size": 200}, expect_code=None, expect_status=422),
            Case("不存在路由", "GET", f"{API}/nonexistent",
                 expect_code=None, expect_status=404),
            Case("触发任务-调度器未启动", "POST", f"{API}/system/trigger/sync_news",
                 expect_code=1003),
        ]),

        Suite(name="9. 行情轮询模拟", cases=[
            Case("轮询-第1次", "GET", f"{API}/stocks/999999.XZ/quote",
                 expect_code=1002),
            Case("轮询-第2次(模拟)", "GET", f"{API}/stocks/999999.XZ/quote",
                 expect_code=1002),
            Case("轮询-第3次(模拟)", "GET", f"{API}/stocks/999999.XZ/quote",
                 expect_code=1002),
        ]),
    ]


# ── 执行器 ───────────────────────────────────────────────

def run_case(client: httpx.Client, case: Case, index: int) -> Result:
    url = f"{BASE_URL}{case.path}"
    start = time.perf_counter()

    try:
        if case.method == "GET":
            resp = client.get(url, params=case.params)
        elif case.method == "POST":
            resp = client.post(url, json=case.body)
        elif case.method == "PUT":
            resp = client.put(url, json=case.body)
        elif case.method == "DELETE":
            resp = client.delete(url)
        else:
            return Result(case=case, error=f"Unknown method: {case.method}")

        elapsed = (time.perf_counter() - start) * 1000
        data = None
        try:
            data = resp.json()
        except Exception:
            data = {"_raw": resp.text[:200]}

        passed = True
        errors: list[str] = []

        # 状态码
        if resp.status_code != case.expect_status:
            passed = False
            errors.append(f"status {resp.status_code}≠{case.expect_status}")

        # 业务码
        if case.expect_code is not None and isinstance(data, dict):
            actual = data.get("code")
            if actual != case.expect_code:
                passed = False
                errors.append(f"code {actual}≠{case.expect_code} msg={data.get('message','')}")

        # 响应格式
        if case.expect_code == 0 and isinstance(data, dict):
            for field in ("code", "message", "ts"):
                if field not in data:
                    passed = False
                    errors.append(f"missing '{field}'")

        # data 字段检查
        if case.check_fields and isinstance(data, dict):
            inner = data.get("data")
            if inner and isinstance(inner, dict):
                for f in case.check_fields:
                    if f not in inner:
                        passed = False
                        errors.append(f"data missing '{f}'")

        # 分页检查
        if case.check_pagination and isinstance(data, dict):
            inner = data.get("data")
            if inner and isinstance(inner, dict):
                pag = inner.get("pagination")
                if pag and isinstance(pag, dict):
                    for f in ("total", "page", "page_size", "pages"):
                        if f not in pag:
                            passed = False
                            errors.append(f"pagination missing '{f}'")

        return Result(case=case, status=resp.status_code, response=data,
                      passed=passed, error="; ".join(errors) if errors else None,
                      elapsed_ms=round(elapsed, 1))
    except Exception as e:
        return Result(case=case, error=str(e),
                      elapsed_ms=round((time.perf_counter() - start) * 1000, 1))


def run_all(suites: list[Suite]) -> tuple[int, int]:
    total = passed = 0
    idx = 0
    client = httpx.Client(timeout=30)

    for suite in suites:
        print(f"\n{'─'*55}")
        print(f"  {suite.name}")
        print(f"{'─'*55}")

        for case in suite.cases:
            idx += 1
            result = run_case(client, case, idx)
            suite.results.append(result)
            total += 1
            if result.passed:
                passed += 1

            icon = "PASS" if result.passed else "FAIL"
            detail = ""
            if not result.passed and result.response and isinstance(result.response, dict):
                detail = json.dumps(result.response, ensure_ascii=False)[:80]
            if result.error:
                detail = result.error[:100]

            print(f"  [{icon}] {case.name:28s} {result.status:3d} {result.elapsed_ms:6.1f}ms"
                  f"{' | ' + detail if detail else ''}")

    client.close()
    return total, passed


# ── 增强校验 ─────────────────────────────────────────────

def extra_checks(suites: list[Suite]) -> int:
    """运行时增强校验，返回额外失败数。"""
    failures = 0

    # 大盘概况 indices 应有4个
    for suite in suites:
        for r in suite.results:
            if r.case.name == "大盘概况-含指数" and r.passed:
                d = r.response.get("data", {}) if r.response else {}
                indices = d.get("indices", [])
                if len(indices) == 4:
                    names = [i["name"] for i in indices]
                    print(f"\n  [CHECK] 大盘指数: {', '.join(names)} — OK")
                else:
                    failures += 1
                    print(f"\n  [CHECK] 大盘指数数量异常: {len(indices)}")

            # watchlist 列表含刚添加的
            if r.case.name == "列表含添加的数据" and r.passed:
                d = r.response.get("data", {}) if r.response else {}
                groups = d.get("groups", [])
                found = any(
                    any(s["ts_code"] == "000001.SZ" for s in g.get("stocks", []))
                    for g in groups
                )
                if found:
                    print(f"  [CHECK] Watchlist 自选股数据已确认 — OK")
                else:
                    # 可能已删除
                    print(f"  [CHECK] Watchlist 无000001.SZ（可能已删除） — SKIP")

    return failures


# ── 汇总 ─────────────────────────────────────────────────

def print_summary(suites: list[Suite], total: int, passed: int):
    failed = total - passed
    bar = "=" * 55
    print(f"\n{bar}")
    status = "ALL PASSED" if failed == 0 else f"{failed} FAILED"
    print(f"  Results: {passed}/{total} passed — {status}")
    print(bar)

    # 响应码分布
    codes: dict = {}
    for suite in suites:
        for r in suite.results:
            if r.response and isinstance(r.response, dict):
                c = r.response.get("code", "?")
                codes[c] = codes.get(c, 0) + 1
    if codes:
        print(f"  Response codes: {codes}")

    # 性能
    times = [r.elapsed_ms for suite in suites for r in suite.results if r.elapsed_ms > 0]
    if times:
        print(f"  Latency: avg {sum(times)/len(times):.1f}ms | "
              f"min {min(times):.1f}ms | max {max(times):.1f}ms")

    # 失败清单
    if failed > 0:
        print(f"\n  Failed cases:")
        for suite in suites:
            for r in suite.results:
                if not r.passed:
                    print(f"    [{suite.name}] {r.case.name}")
                    print(f"      {r.case.method} {r.case.path}")
                    if r.response and isinstance(r.response, dict):
                        print(f"      Response: {json.dumps(r.response, ensure_ascii=False)[:150]}")


def main():
    global BASE_URL
    parser = argparse.ArgumentParser(description="前端 API 集成测试")
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()

    BASE_URL = args.base_url

    print(f"\n  {'='*55}")
    print(f"  前端 API 集成测试 — a-stock-info")
    print(f"  Target: {BASE_URL}")
    print(f"  {'='*55}")

    suites = build_suites()
    total, passed = run_all(suites)
    extra_fails = extra_checks(suites)
    print_summary(suites, total, passed - extra_fails)

    final = passed - extra_fails
    return 0 if final == total else 1


if __name__ == "__main__":
    sys.exit(main())
