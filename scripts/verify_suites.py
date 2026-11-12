import asyncio
import json
from pathlib import Path
from time import perf_counter

from agentbench.agents.langgraph_adapter import execute_graph
from agentbench.evaluation.scoring import score
from agentbench.mcp.client import Sandbox
from agentbench.schemas import AgentConfig, DatasetFile


async def main():
    start = perf_counter()
    failures, suites = [], {}
    async with Sandbox(transport="stdio") as sandbox:
        for path in sorted(Path("datasets").glob("*/v1.json")):
            dataset = DatasetFile.model_validate_json(path.read_text())
            results = []
            for case in dataset.cases:
                execution = await execute_graph(
                    AgentConfig(name="Verification supervisor", version="1", workflow="supervisor"),
                    case,
                    sandbox,
                )
                result = score(case, execution)
                results.append(result)
                if not result.passed:
                    failure = {
                        "case": case.id,
                        "output": execution.output,
                        "errors": execution.errors,
                        "metrics": [
                            m.model_dump()
                            for m in result.metrics
                            if m.status not in {"PASS", "NOT_APPLICABLE"}
                        ],
                    }
                    failures.append(failure)
                    print(json.dumps(failure), flush=True)
            suites[dataset.name] = {"total": len(results), "passed": sum(r.passed for r in results)}
            print(dataset.name, suites[dataset.name], flush=True)
    report = {"suites": suites, "failures": failures, "elapsed_seconds": perf_counter() - start}
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/suite-verification.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "failures"}), flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
