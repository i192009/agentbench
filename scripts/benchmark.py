"""Measure bounded offline execution admission loads using real MCP connections.

CPU/RSS measurements apply to this benchmark driver, not the separate MCP/DB services.
"""

import argparse
import asyncio
import json
import time
from pathlib import Path

import psutil
from agentbench.agents.langgraph_adapter import execute_graph
from agentbench.evaluation.scoring import score
from agentbench.mcp.client import Sandbox
from agentbench.schemas import AgentConfig, DatasetFile


async def main(args):
    cases = DatasetFile.model_validate_json(Path("datasets/ci.json").read_text()).cases
    report = {
        "scope": "benchmark driver + real MCP protocol; bounded admission queue; excludes PostgreSQL persistence and MLflow tracking",
        "concurrency": args.concurrency,
        "loads": [],
    }
    process = psutil.Process()
    async with Sandbox() as sandbox:
        for count in args.counts:
            queue = asyncio.Queue(maxsize=count)
            start = time.perf_counter()
            cpu_start = sum(process.cpu_times()[:2])
            waits, latencies, sizes, failures = [], [], [], []
            for i in range(count):
                queue.put_nowait((i, time.perf_counter()))

            async def worker(
                queue=queue, waits=waits, count=count, latencies=latencies, sizes=sizes, failures=failures
            ):
                while not queue.empty():
                    i, enqueued = queue.get_nowait()
                    waits.append((time.perf_counter() - enqueued) * 1000)
                    case = cases[i % len(cases)].model_copy(deep=True)
                    case.id = f"benchmark-{count}-{i}"
                    result = await execute_graph(AgentConfig(name="Benchmark", version="v1"), case, sandbox)
                    latencies.append(result.latency_ms)
                    sizes.append(len(result.model_dump_json().encode()))
                    if not score(case, result).passed:
                        failures.append(case.id)
                    queue.task_done()

            await asyncio.gather(*(worker() for _ in range(min(args.concurrency, count))))
            elapsed = time.perf_counter() - start
            import numpy as np

            measurement = {
                "submitted_cases": count,
                "passed": count - len(failures),
                "elapsed_seconds": elapsed,
                "cases_per_second": count / elapsed,
                "queue_wait_p95_ms": float(np.percentile(waits, 95)),
                "latency_p50_ms": float(np.percentile(latencies, 50)),
                "latency_p95_ms": float(np.percentile(latencies, 95)),
                "driver_rss_mb": process.memory_info().rss / 1024**2,
                "driver_cpu_seconds": sum(process.cpu_times()[:2]) - cpu_start,
                "average_trace_bytes": sum(sizes) / count,
                "failures": failures,
            }
            report["loads"].append(measurement)
            print(json.dumps(measurement), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if any(load["failures"] for load in report["loads"]):
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--counts", type=int, nargs="+", default=[10, 50, 100, 500])
    parser.add_argument("--concurrency", type=int, choices=range(1, 17), default=4)
    parser.add_argument("--output", type=Path, default=Path("artifacts/benchmark.json"))
    args = parser.parse_args()
    if any(count < 1 or count > 2000 for count in args.counts):
        parser.error("counts must be between 1 and 2000")
    asyncio.run(main(args))
