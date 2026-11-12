import asyncio
from pathlib import Path

from agentbench.agents.langgraph_adapter import execute_graph
from agentbench.evaluation.extensions import deepeval_metrics, ragas_metrics
from agentbench.evaluation.scoring import score
from agentbench.mcp.client import Sandbox
from agentbench.schemas import AgentConfig, DatasetFile


async def main():
    async with Sandbox() as sandbox:
        print("Discovered MCP tools:", len(sandbox.schemas), flush=True)
        for suite, workflow in [
            ("financial-research", "research"),
            ("financial-operations", "operations"),
            ("rag", "research"),
        ]:
            dataset = DatasetFile.model_validate_json(Path(f"datasets/{suite}/v1.json").read_text())
            case = dataset.cases[12 if workflow == "operations" else 0]
            execution = await execute_graph(
                AgentConfig(name="smoke", version="1", workflow=workflow), case, sandbox
            )
            result = score(case, execution)
            print(case.id, execution.status, execution.output, execution.errors, flush=True)
            print(
                "Failed metrics",
                [m.model_dump() for m in result.metrics if m.status not in {"PASS", "NOT_APPLICABLE"}],
                flush=True,
            )
            print("Ragas", [m.model_dump() for m in await ragas_metrics(case, execution)], flush=True)
            print("DeepEval", [m.model_dump() for m in await deepeval_metrics(case, execution)], flush=True)


if __name__ == "__main__":
    asyncio.run(main())
