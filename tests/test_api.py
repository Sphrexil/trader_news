"""API 批量接口测试脚本。

用法:
    python tests/test_api.py
    python tests/test_api.py --base-url http://localhost:8001
    python tests/test_api.py --verbose
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

# ── 配置 ───────────────────────────────────────────────────

BASE_URL = "http://localhost:8001"
API = "/api/v1"


# ── 测试结果 ───────────────────────────────────────────────

@dataclass
class Case:
    name: str
    method: str
    path: str
    params: dict | None = None
    body: dict | None = None
    expect_code: int = 0
    expect_status: int = 200

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


# ── 测试用例定义 ──────────────────────────────────────────

def build_suites() -> list[Suite]:
    return [
        Suite(name="System", cases=[
            Case("健康检查", "GET", "/health", expect_code=None),
            Case("根路径", "GET", "/", expect_code=None),
            Case("服务状态", "GET", f"{API}/system/status"),
            Case("触发不存在的任务", "POST", f"{API}/system/trigger/fake_job", expect_code=1003),
        ]),
        Suite(name="Stocks", cases=[
            Case("股票搜索（无关键字）", "GET", f"{API}/stocks", params={"page": 1, "page_size": 5}),
            Case("股票搜索（关键字）", "GET", f"{API}/stocks", params={"q": "平安", "page": 1, "page_size": 5}),
            Case("股票搜索（市场筛选）", "GET", f"{API}/stocks", params={"market": "SH", "page": 1, "page_size": 5}),
            Case("个股详情（不存在）", "GET", f"{API}/stocks/000001.SZ", expect_code=1002),
            Case("行情快照（不存在）", "GET", f"{API}/stocks/000001.SZ/quote", expect_code=1002),
            Case("K线数据", "GET", f"{API}/stocks/000001.SZ/kline", params={"period": "daily", "limit": 10}),
            Case("财务数据", "GET", f"{API}/stocks/000001.SZ/financials", params={"report_type": "Q", "limit": 4}),
            Case("公告列表", "GET", f"{API}/stocks/000001.SZ/announcements", params={"page": 1, "page_size": 5}),
        ]),
        Suite(name="Market", cases=[
            Case("大盘概况", "GET", f"{API}/market/overview"),
            Case("板块涨跌（行业）", "GET", f"{API}/market/sectors", params={"type": "industry"}),
        ]),
        Suite(name="News", cases=[
            Case("新闻列表", "GET", f"{API}/news", params={"page": 1, "page_size": 5}),
            Case("新闻列表（来源筛选）", "GET", f"{API}/news", params={"source": "东方财富", "page": 1, "page_size": 5}),
        ]),
        Suite(name="Watchlist CRUD", cases=[
            Case("[C] 添加自选股", "POST", f"{API}/watchlist",
                 body={"ts_code": "600000.SH", "group_name": f"测试组{int(time.time())}", "note": "API测试", "cost_price": 7.50},
                 expect_status=201),
            Case("[R] 获取自选股", "GET", f"{API}/watchlist"),
        ]),
        Suite(name="Alerts CRUD", cases=[
            Case("[C] 创建告警", "POST", f"{API}/alerts",
                 body={"ts_code": "600000.SH", "rule_type": "price_abs", "threshold": 10.0,
                       "direction": "above", "channel": "bark", "channel_cfg": {"bark_key": "test"}},
                 expect_status=201),
            Case("[R] 获取告警列表", "GET", f"{API}/alerts"),
        ]),
        Suite(name="Error Handling", cases=[
            Case("参数校验-分页超限", "GET", f"{API}/stocks", params={"page_size": 200}, expect_code=None, expect_status=422),
            Case("不存在的路由", "GET", f"{API}/nonexistent", expect_code=None, expect_status=404),
        ]),
    ]


# ── 测试执行 ──────────────────────────────────────────────

def run_case(client: httpx.Client, case: Case) -> Result:
    url = f"{BASE_URL}{case.path}"
    start = time.perf_counter()

    try:
        if case.method == "GET":
            resp = client.get(url, params=case.params)
        elif case.method == "POST":
            resp = client.post(url, json=case.body, params=case.params)
        elif case.method == "PUT":
            resp = client.put(url, json=case.body, params=case.params)
        elif case.method == "DELETE":
            resp = client.delete(url, params=case.params)
        else:
            return Result(case=case, error=f"Unknown method: {case.method}")

        elapsed = (time.perf_counter() - start) * 1000
        data = None
        try:
            data = resp.json()
        except Exception:
            data = resp.text

        # 验证
        passed = True
        errors = []

        # 状态码
        if resp.status_code != case.expect_status:
            passed = False
            errors.append(f"status={resp.status_code}(expected {case.expect_status})")

        # 业务错误码（仅当 expect_code 不为 None 时检查）
        if case.expect_code is not None and isinstance(data, dict):
            if data.get("code") != case.expect_code:
                passed = False
                errors.append(f"code={data.get('code')}(expected {case.expect_code})")

        # 通用响应格式检查
        if isinstance(data, dict) and case.expect_code == 0:
            if "code" not in data:
                passed = False
                errors.append("missing 'code' field")
            if "message" not in data:
                passed = False
                errors.append("missing 'message' field")
            if "ts" not in data:
                passed = False
                errors.append("missing 'ts' field")

        return Result(
            case=case, status=resp.status_code, response=data,
            passed=passed, error="; ".join(errors) if errors else None,
            elapsed_ms=round(elapsed, 1),
        )
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return Result(case=case, error=str(e), elapsed_ms=round(elapsed, 1))


def run_all(suites: list[Suite], verbose: bool = False) -> tuple[int, int]:
    total = 0
    passed = 0
    client = httpx.Client(timeout=30)

    for suite in suites:
        if verbose:
            print(f"\n{'='*60}")
            print(f"  {suite.name}")
            print(f"{'='*60}")

        for case in suite.cases:
            result = run_case(client, case)
            suite.results.append(result)
            total += 1
            if result.passed:
                passed += 1

            if verbose:
                status_icon = "PASS" if result.passed else "FAIL"
                print(f"  [{status_icon}] {case.name:30s} {result.status:3d} {result.elapsed_ms:6.1f}ms"
                      f"{' — ' + result.error if result.error else ''}")
        if not verbose:
            suite_passed = sum(1 for r in suite.results if r.passed)
            print(f"  {suite.name:20s}  {suite_passed}/{len(suite.cases)} passed")

    client.close()
    return total, passed


# ── 摘要报告 ──────────────────────────────────────────────

def print_summary(suites: list[Suite], total: int, passed: int):
    failed = total - passed
    print(f"\n{'='*60}")
    print(f"  Results: {passed}/{total} passed"
          f"{' (ALL PASSED)' if failed == 0 else f', {failed} FAILED'}")
    print(f"{'='*60}")

    if failed > 0:
        print("\n  Failed cases:")
        for suite in suites:
            for r in suite.results:
                if not r.passed:
                    print(f"    [{suite.name}] {r.case.name}")
                    print(f"      {r.case.method} {r.case.path}")
                    if r.error:
                        print(f"      Error: {r.error}")
                    if r.response and isinstance(r.response, dict):
                        print(f"      Response: {json.dumps(r.response, ensure_ascii=False)[:200]}")

    # 响应格式统计
    api_cases = [r for suite in suites for r in suite.results
                 if r.response and isinstance(r.response, dict) and "code" in r.response]
    if api_cases:
        codes = {}
        for r in api_cases:
            c = r.response.get("code", "?")
            codes[c] = codes.get(c, 0) + 1
        print(f"\n  Response code distribution: {codes}")

    # 性能
    all_elapsed = [r.elapsed_ms for suite in suites for r in suite.results]
    if all_elapsed:
        avg = sum(all_elapsed) / len(all_elapsed)
        print(f"  Avg latency: {avg:.1f}ms  |  Min: {min(all_elapsed):.1f}ms  |  Max: {max(all_elapsed):.1f}ms")


def main():
    global BASE_URL
    parser = argparse.ArgumentParser(description="a-stock-info API 批量测试")
    parser.add_argument("--base-url", default=BASE_URL, help="API base URL")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    args = parser.parse_args()

    BASE_URL = args.base_url

    print(f"\n  a-stock-info API 批量测试")
    print(f"  Target: {BASE_URL}")
    print(f"  {'─'*50}")

    suites = build_suites()
    total, passed = run_all(suites, verbose=args.verbose)
    print_summary(suites, total, passed)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
