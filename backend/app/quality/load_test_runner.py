"""
Progressive Concurrency & Stress Testing Simulator.
Simulates progressive traffic up to 1,000 concurrent users:
Stages: 10 -> 50 -> 100 -> 250 -> 500 -> 750 -> 1,000.
Monitors latency degradation, error rates, CPU%, and Memory consumption.
Halts progression upon critical bottleneck detection.
"""

from __future__ import annotations

import asyncio
import logging
import math
import time

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import LoadTestRun
from app.quality.schemas import LoadTestStageResult

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


LOAD_STAGES = [
    (1, 10, 50),     # stage, concurrency, requests
    (2, 50, 150),
    (3, 100, 300),
    (4, 250, 500),
    (5, 500, 750),
    (6, 750, 1000),
    (7, 1000, 1200),
]


class LoadTestRunner:
    """
    Executes progressive multi-stage load simulation and records detailed performance metrics.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        db: AsyncSession | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.db = db

    def _sample_resources(self) -> tuple[float | None, float | None]:
        if psutil is None:
            return None, None
        try:
            process = psutil.Process()
            cpu = process.cpu_percent(interval=0.05)
            mem_mb = process.memory_info().rss / (1024 * 1024)
            return round(cpu, 1), round(mem_mb, 1)
        except Exception:
            return None, None

    async def run_progressive_load_test(
        self,
        project_id: str,
        test_path: str = "/api/v1/health",
        max_stages: int = 7,
    ) -> list[LoadTestStageResult]:
        """
        Execute progressive load test stages up to max_stages or until bottleneck failure.
        """
        results: list[LoadTestStageResult] = []
        target_url = f"{self.base_url}{test_path}" if test_path.startswith("/") else f"{self.base_url}/{test_path}"

        for stage_idx, target_users, req_count in LOAD_STAGES[:max_stages]:
            logger.info(
                "Starting Load Test Stage %d: %d concurrent users (%d requests)",
                stage_idx,
                target_users,
                req_count,
            )

            cpu_before, mem_before = self._sample_resources()
            latencies_ms: list[float] = []
            successful = 0
            failed = 0
            bottlenecks: list[str] = []

            start_wall = time.perf_counter()
            semaphore = asyncio.Semaphore(target_users)

            async with httpx.AsyncClient(timeout=5.0) as client:

                async def _worker(
                    sem: asyncio.Semaphore = semaphore,
                    latencies: list[float] = latencies_ms,
                ) -> None:
                    nonlocal successful, failed
                    async with sem:
                        t0 = time.perf_counter()
                        try:
                            resp = await client.get(target_url)
                            dur = (time.perf_counter() - t0) * 1000.0
                            if resp.status_code < 500:
                                successful += 1
                                latencies.append(dur)
                            else:
                                failed += 1
                                latencies.append(dur)
                        except Exception:
                            failed += 1

                tasks = [_worker() for _ in range(req_count)]
                await asyncio.gather(*tasks)

            total_dur = time.perf_counter() - start_wall
            cpu_after, mem_after = self._sample_resources()
            cpu_val = cpu_after or cpu_before
            mem_val = mem_after or mem_before

            rps = round(len(latencies_ms) / total_dur, 2) if total_dur > 0 else 0.0
            latencies_ms.sort()

            avg_lat = sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0
            p50 = calculate_percentile(latencies_ms, 50)
            p90 = calculate_percentile(latencies_ms, 90)
            p95 = calculate_percentile(latencies_ms, 95)
            p99 = calculate_percentile(latencies_ms, 99)
            max_lat = round(latencies_ms[-1], 2) if latencies_ms else 0.0

            error_rate = (failed / req_count) if req_count > 0 else 0.0

            # Evaluate bottleneck triggers
            stage_status = "passed"
            if error_rate > 0.05:
                bottlenecks.append(f"High error rate ({round(error_rate * 100, 1)}% > 5%)")
                stage_status = "failed"
            if p95 > 1000.0:
                bottlenecks.append(f"P95 latency exceeded 1000ms ({p95}ms)")
                stage_status = "failed"
            if cpu_val and cpu_val > 90.0:
                bottlenecks.append(f"Sustained CPU saturation ({cpu_val}%)")

            stage_result = LoadTestStageResult(
                stage=stage_idx,
                target_concurrency=target_users,
                actual_concurrency=min(target_users, req_count),
                total_requests=req_count,
                successful_requests=successful,
                failed_requests=failed,
                requests_per_second=rps,
                avg_latency_ms=round(avg_lat, 2),
                p95_latency_ms=p95,
                p99_latency_ms=p99,
                cpu_percent=cpu_val,
                memory_mb=mem_val,
                status=stage_status,
                bottlenecks=bottlenecks,
            )
            results.append(stage_result)

            # Persist record to DB if session provided
            if self.db:
                record = LoadTestRun(
                    project_id=project_id,
                    stage=stage_idx,
                    target_concurrency=target_users,
                    actual_concurrency=stage_result.actual_concurrency,
                    total_requests=req_count,
                    successful_requests=successful,
                    failed_requests=failed,
                    requests_per_second=rps,
                    avg_latency_ms=round(avg_lat, 2),
                    p50_latency_ms=p50,
                    p90_latency_ms=p90,
                    p95_latency_ms=p95,
                    p99_latency_ms=p99,
                    max_latency_ms=max_lat,
                    cpu_percent=cpu_val,
                    memory_mb=mem_val,
                    status=stage_status,
                    error_summary="; ".join(bottlenecks) if bottlenecks else None,
                    bottlenecks=[{"description": b} for b in bottlenecks],
                )
                self.db.add(record)
                await self.db.commit()

            # Stop-on-failure: if this stage failed severely, do not overload system further
            if stage_status == "failed" and error_rate > 0.3:
                logger.warning(
                    "Halting load test at stage %d due to severe error rate (%.1f%%)",
                    stage_idx,
                    error_rate * 100,
                )
                break

        return results
