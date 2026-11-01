"""
Performance and Resource Benchmark Runner.
Measures latency distribution (avg, P50, P90, P95, P99, max),
throughput (RPS), and system resource usage (CPU%, Memory MB).
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from typing import Any

import httpx

from app.quality.schemas import PerformanceMetrics

logger = logging.getLogger(__name__)

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore[assignment]


def calculate_percentile(data: list[float], percentile: float) -> float:
    """Calculate the k-th percentile of a sorted list of floats."""
    if not data:
        return 0.0
    k = (len(data) - 1) * (percentile / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return round(data[int(k)], 2)
    d0 = data[int(f)] * (c - k)
    d1 = data[int(c)] * (k - f)
    return round(d0 + d1, 2)


class PerformanceRunner:
    """
    Executes benchmark queries against target service endpoints and profiles system resources.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8000") -> None:
        self.base_url = base_url.rstrip("/")

    def get_resource_usage(self) -> tuple[float | None, float | None]:
        """Capture current process CPU percentage and memory in MB."""
        if psutil is None:
            return None, None
        try:
            process = psutil.Process()
            cpu = process.cpu_percent(interval=0.1)
            mem_mb = process.memory_info().rss / (1024 * 1024)
            return round(cpu, 1), round(mem_mb, 1)
        except Exception:
            return None, None

    async def benchmark_endpoint(
        self,
        endpoint: str = "/api/v1/health",
        method: str = "GET",
        total_requests: int = 100,
        concurrency: int = 10,
        headers: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> PerformanceMetrics:
        """
        Send total_requests with specified concurrency to profile latency distribution.
        """
        url = f"{self.base_url}{endpoint}" if endpoint.startswith("/") else f"{self.base_url}/{endpoint}"
        latencies_ms: list[float] = []
        errors = 0

        cpu_start, mem_start = self.get_resource_usage()
        start_time = time.perf_counter()

        semaphore = asyncio.Semaphore(concurrency)
        async with httpx.AsyncClient(timeout=10.0) as client:

            async def _send_request() -> None:
                nonlocal errors
                async with semaphore:
                    req_start = time.perf_counter()
                    try:
                        if method.upper() == "GET":
                            resp = await client.get(url, headers=headers)
                        elif method.upper() == "POST":
                            resp = await client.post(url, headers=headers, json=payload)
                        else:
                            resp = await client.request(method.upper(), url, headers=headers, json=payload)
                        elapsed_ms = (time.perf_counter() - req_start) * 1000.0
                        if resp.status_code < 500:
                            latencies_ms.append(elapsed_ms)
                        else:
                            errors += 1
                    except Exception:
                        errors += 1

            tasks = [_send_request() for _ in range(total_requests)]
            await asyncio.gather(*tasks)

        total_elapsed = time.perf_counter() - start_time
        cpu_end, mem_end = self.get_resource_usage()

        if not latencies_ms:
            # If target server was unreachable or all failed
            return PerformanceMetrics(
                avg_latency_ms=0.0,
                p50_latency_ms=0.0,
                p90_latency_ms=0.0,
                p95_latency_ms=0.0,
                p99_latency_ms=0.0,
                max_latency_ms=0.0,
                requests_per_second=0.0,
                total_requests=total_requests,
                cpu_percent=cpu_end or cpu_start,
                memory_mb=mem_end or mem_start,
            )

        latencies_ms.sort()
        avg_lat = sum(latencies_ms) / len(latencies_ms)
        rps = round(len(latencies_ms) / total_elapsed, 2) if total_elapsed > 0 else 0.0

        return PerformanceMetrics(
            avg_latency_ms=round(avg_lat, 2),
            p50_latency_ms=calculate_percentile(latencies_ms, 50),
            p90_latency_ms=calculate_percentile(latencies_ms, 90),
            p95_latency_ms=calculate_percentile(latencies_ms, 95),
            p99_latency_ms=calculate_percentile(latencies_ms, 99),
            max_latency_ms=round(latencies_ms[-1], 2),
            requests_per_second=rps,
            total_requests=total_requests,
            cpu_percent=cpu_end or cpu_start,
            memory_mb=mem_end or mem_start,
        )

