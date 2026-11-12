"""MLflow owns experiment views; PostgreSQL owns AgentBench results."""

from agentbench.config import settings
from agentbench.schemas import CaseResult


def log_run(run_id: str, snapshot: dict, summary: dict, results: list[CaseResult]) -> dict:
    uri = settings().mlflow_tracking_uri
    if not uri:
        return {"status": "DISABLED", "reason": "AB_MLFLOW_TRACKING_URI is unset"}
    try:
        import mlflow
        from mlflow.genai.scorers import scorer

        mlflow.set_tracking_uri(uri)
        experiment = mlflow.set_experiment("AgentBench/" + snapshot["dataset"]["name"])

        @scorer(name="agentbench_case_pass")
        def case_pass(outputs):
            # Reuse the authoritative evaluation result, never recalculate an alternate metric.
            return bool(outputs["passed"])

        with mlflow.start_run(run_name=run_id, experiment_id=experiment.experiment_id) as tracked:
            mlflow.log_params(
                {
                    "agentbench_run_id": run_id,
                    "agent_version": snapshot["agent"]["version"],
                    "agent_checksum": snapshot["agent_checksum"],
                    "dataset_checksum": snapshot["dataset_checksum"],
                    "dataset_version": snapshot["dataset"]["version"],
                    "mode": snapshot["request"]["mode"],
                    "prompt_version": snapshot["agent"]["prompt_version"],
                    "model": str(snapshot["agent"]["model"]),
                }
            )
            mlflow.log_metrics(
                {
                    key: float(value)
                    for key, value in summary.items()
                    if isinstance(value, (int, float)) and not isinstance(value, bool)
                }
            )
            mlflow.log_metrics({"score_" + k: v for k, v in summary["metrics"].items()})
            mlflow.log_dict(summary, "report.json")
            mlflow.log_dict(snapshot, "snapshot.json")
            for result in results:
                with mlflow.start_span(name="agentbench.case", span_type="AGENT") as span:
                    span.set_inputs({"case_id": result.case_id, "agentbench_run_id": run_id})
                    span.set_outputs({"passed": result.passed, "output": result.execution.output})
                    span.set_attributes(
                        {
                            "mode": result.execution.mode,
                            "agentbench_trace_id": result.execution.trace[0].trace_id
                            if result.execution.trace
                            else "missing",
                        }
                    )
                mlflow.log_dict(result.execution.model_dump(mode="json"), f"traces/{result.case_id}.json")
            evaluation = mlflow.genai.evaluate(
                data=[{"inputs": {"case_id": r.case_id}, "outputs": {"passed": r.passed}} for r in results],
                scorers=[case_pass],
            )
            return {
                "status": "RECORDED",
                "run_id": tracked.info.run_id,
                "genai_evaluation_run_id": evaluation.run_id,
                "tracking_uri": uri,
                "experiment_id": experiment.experiment_id,
            }
    except Exception as exc:
        return {"status": "ERROR", "reason": f"{type(exc).__name__}: {str(exc)[:1000]}"}
