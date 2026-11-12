"""Synthetic fixtures matching inspected native contracts; not captured application runs."""

from pathlib import Path

from agentbench.schemas import AgentConfig, DatasetFile, TestCase

root = Path(__file__).resolve().parents[1]
directory = root / "examples" / "repository-contracts"
directory.mkdir(parents=True, exist_ok=True)
for adapter in ["finsight", "ledgerguard"]:
    records, cases = {}, []
    for index in range(12):
        case_id = f"{adapter}-{index + 1:03}"
        if adapter == "finsight":
            gold = [25, -20, 0, 100, -100, 10, 50, 5, 75, 12.5, 20, 30][index]
            text = f"ACME revenue growth is {gold} percent."
            body = {
                "title": "Synthetic ACME research",
                "companies": [{"ticker": "ACME", "cik": "0000000001", "name": "ACME Synthetic"}],
                "generated_at": "2026-01-01T00:00:00Z",
                "data_cutoff": "2025-12-31",
                "sections": [
                    {
                        "heading": "Growth",
                        "claims": [
                            {
                                "text": text,
                                "kind": "evidence_summary",
                                "citations": ["calculation:1"],
                                "evidence_quotes": [{"source_id": "calculation:1", "quote": text}],
                            }
                        ],
                    }
                ],
                "facts": [],
                "calculations": [
                    {
                        "ticker": "ACME",
                        "metric": "revenue_growth",
                        "value": str(gold),
                        "unit": "%",
                        "formula": "(current revenue / prior revenue - 1) * 100",
                        "sources": [],
                    }
                ],
                "sources": [
                    {
                        "id": "calculation:1",
                        "source_url": "https://synthetic.invalid/filing",
                        "content": text,
                        "facts": {"growth_percent": gold},
                    }
                ],
                "limitations": ["Synthetic contract fixture; original application not executed"],
                "disclosure": "Not investment advice. Synthetic data.",
                "status": "completed",
            }
            records[case_id] = {
                "report": {
                    "id": f"00000000-0000-4000-8000-{index + 1:012}",
                    "title": body["title"],
                    "status": "completed",
                    "created_at": body["generated_at"],
                    "companies": body["companies"],
                    "body": body,
                },
                "claim_bindings": {text: "growth_percent"},
                "tool_calls": [
                    {"name": "search_companies", "arguments": {"query": "ACME"}, "status": "ok"},
                    {
                        "name": "get_company_financial_facts",
                        "arguments": {
                            "ticker": "ACME",
                            "metrics": ["revenue"],
                            "periods": 3,
                            "period": "annual",
                        },
                        "status": "ok",
                    },
                ],
                "nodes": [
                    "REQUEST_ANALYSIS_NODE",
                    "COMPANY_RESOLUTION_NODE",
                    "FINANCIAL_DATA_NODE",
                    "FINANCIAL_CALCULATION_NODE",
                ],
            }
            expectation = {
                "facts": {"growth_percent": gold},
                "required_tools": ["search_companies", "get_company_financial_facts"],
                "arguments": {"get_company_financial_facts": {"ticker": "ACME", "period": "annual"}},
                "citation_ids": ["calculation:1"],
                "document_ids": ["calculation:1"],
            }
            prompt = "Validate this recorded synthetic FinSight financial research report and accompanying tool telemetry."
        else:
            approved = index % 3 == 0
            state = {
                "run_id": f"native-{index}",
                "request": "Review ACC-1",
                "approval_ids": [f"approval-{index}"],
                "executions": [{"id": f"execution-{index}", "simulated": True}] if approved else [],
                "report_id": f"report-{index}",
            }
            events = [
                {"event": "RUN_STARTED", "data": {}},
                {"event": "AGENT_STARTED", "data": {"agent": "Transaction Analysis"}},
                {"event": "APPROVAL_REQUIRED", "data": {"approval_ids": state["approval_ids"]}},
                {
                    "event": "APPROVAL_RECEIVED",
                    "data": {
                        "statuses": ["APPROVED" if approved else "REJECTED" if index % 3 == 1 else "EXPIRED"]
                    },
                },
            ]
            if approved:
                events.append({"event": "ACTION_EXECUTED", "data": {"execution_id": f"execution-{index}"}})
            events.append({"event": "RUN_COMPLETED", "data": {"report_id": state["report_id"]}})
            records[case_id] = {
                "run": {"id": state["run_id"], "status": "COMPLETED", "state": state, "error": None},
                "events": events,
                "tool_executions": [
                    {
                        "server": "transactions",
                        "tool": "get_account_transaction_summary",
                        "duration_ms": 0,
                        "status": "SUCCESS",
                        "details": {"arguments": {"account_id": "ACC-1"}},
                    },
                    {
                        "server": "approvals",
                        "tool": "create_approval_request",
                        "duration_ms": 0,
                        "status": "SUCCESS",
                        "details": {"arguments": {"proposed_action_id": f"action-{index}"}},
                    },
                ],
            }
            expectation = {
                "output": {"executed": approved, "report_created": True},
                "required_tools": ["get_account_transaction_summary", "create_approval_request"],
                "require_evidence": False,
            }
            prompt = "Validate this recorded synthetic LedgerGuard workflow and human-approval events."
        cases.append(TestCase(id=case_id, category=adapter + "-contract", input=prompt, expected=expectation))
    config = AgentConfig(
        name="FinSight AI contract" if adapter == "finsight" else "LedgerGuard AI contract",
        version="v1",
        adapter=adapter,
        workflow="research" if adapter == "finsight" else "operations",
        runtime={"records": records},
    )
    (directory / f"{adapter}-agent.json").write_text(
        config.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    suite = DatasetFile(
        name=adapter + "-contract",
        domain=adapter,
        cases=cases,
        provenance={"kind": "synthetic-native-contract", "original_application_executed": False},
    )
    (directory / f"{adapter}-dataset.json").write_text(
        suite.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
