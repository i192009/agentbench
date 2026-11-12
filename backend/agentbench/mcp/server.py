"""Four deterministic synthetic MCP services, served over stdio or Streamable HTTP.

Fixtures are data only. No filesystem, shell, URL fetch, or real financial side effect exists.
"""

import argparse
import asyncio
import math
import os
import re
from decimal import Decimal
from typing import Any

from mcp.server.fastmcp import FastMCP

GROUPS = {
    "financial": [
        "get_company_profile",
        "get_financial_statements",
        "get_revenue_history",
        "calculate_financial_ratio",
        "search_financial_filings",
    ],
    "transactions": [
        "list_transactions",
        "get_transaction",
        "find_duplicate_transactions",
        "get_account_balances",
        "search_transaction_history",
    ],
    "risk": [
        "assess_transaction_risk",
        "detect_transaction_anomalies",
        "compare_ledger_entries",
        "find_reconciliation_discrepancies",
        "generate_reconciliation_report",
    ],
    "approvals": [
        "create_approval_request",
        "get_approval_status",
        "list_pending_approvals",
        "cancel_approval_request",
        "resolve_approval",
        "execute_correction",
    ],
}


async def fault(scenario: dict, name: str):
    injection = scenario.get("fault", {})
    if injection.get("tool") != name:
        return
    kind = injection.get("kind")
    if kind == "temporary" and scenario.get("attempt", 1) == 1:
        raise ValueError("TEMPORARY: synthetic unavailable tool")
    if kind in {"slow", "timeout"}:
        await asyncio.sleep(min(float(injection.get("seconds", 0.1)), 5))
    if kind == "error":
        raise ValueError("PERMANENT: synthetic tool error")


def create_server(group: str) -> FastMCP:
    server = FastMCP(
        f"AgentBench-{group}",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        stateless_http=True,
        json_response=True,
    )
    approvals: dict[str, dict] = {}
    executions: dict[str, dict] = {}

    @server.tool()
    async def get_company_profile(company: str, scenario: dict[str, Any]) -> dict:
        """Resolve a synthetic company unambiguously."""
        await fault(scenario, "get_company_profile")
        candidates = scenario.get("companies", [company])
        return {"company": company, "candidates": candidates, "ambiguous": len(candidates) != 1}

    @server.tool()
    async def get_financial_statements(company: str, period: int, scenario: dict[str, Any]) -> dict:
        """Return exact minor-unit synthetic statements for a reporting period."""
        await fault(scenario, "get_financial_statements")
        if company != scenario.get("company", "ACME"):
            raise ValueError("Unknown synthetic issuer")
        if scenario.get("fault", {}).get("kind") == "malformed":
            return {"unexpected": "not a statement"}
        if scenario.get("missing") or scenario.get("fault", {}).get("kind") == "empty":
            return {"statements": [], "currency": scenario.get("currency", "USD")}
        return {
            "statements": [x for x in scenario.get("statements", []) if x["period"] in [period, period - 1]],
            "currency": scenario.get("currency", "USD"),
        }

    @server.tool()
    async def get_revenue_history(company: str, scenario: dict[str, Any]) -> dict:
        """Return synthetic revenue history."""
        return {"company": company, "history": scenario.get("statements", [])}

    @server.tool()
    async def calculate_financial_ratio(
        numerator_minor: int, denominator_minor: int, scenario: dict[str, Any]
    ) -> dict:
        """Calculate a percentage using Decimal; reject a zero denominator."""
        if not denominator_minor:
            raise ValueError("Zero denominator")
        return {"percent": str(Decimal(numerator_minor) / Decimal(denominator_minor) * 100)}

    @server.tool()
    async def search_financial_filings(company: str, query: str, scenario: dict[str, Any]) -> dict:
        """Return ordered, versioned synthetic filing evidence, possibly adversarial."""
        await fault(scenario, "search_financial_filings")
        terms = set(re.findall(r"\w+", query.casefold()))
        source_docs = scenario.get("documents", [])
        document_terms = [set(re.findall(r"\w+", d["content"].casefold())) for d in source_docs]
        weights = {
            term: 1 + math.log((len(source_docs) + 1) / (1 + sum(term in words for words in document_terms)))
            for term in terms
        }
        documents = [
            doc
            for _, doc in sorted(
                zip(document_terms, source_docs, strict=True),
                key=lambda pair: sum(weights[t] for t in terms & pair[0]),
                reverse=True,
            )
        ]
        return {"company": company, "documents": documents, "untrusted_text": scenario.get("injection", "")}

    @server.tool()
    async def list_transactions(account_id: str, scenario: dict[str, Any]) -> dict:
        """List transactions only for the requested synthetic account."""
        await fault(scenario, "list_transactions")
        return {
            "transactions": [t for t in scenario.get("transactions", []) if t["account_id"] == account_id],
            "untrusted_text": scenario.get("injection", ""),
        }

    @server.tool()
    async def get_transaction(transaction_id: str, scenario: dict[str, Any]) -> dict:
        """Retrieve one synthetic transaction."""
        matches = [t for t in scenario.get("transactions", []) if t["id"] == transaction_id]
        if not matches:
            raise ValueError("Transaction evidence missing")
        return matches[0]

    @server.tool()
    async def find_duplicate_transactions(account_id: str, scenario: dict[str, Any]) -> dict:
        """Detect equal reference, amount and currency within an account."""
        seen, duplicates = set(), []
        for tx in scenario.get("transactions", []):
            if tx["account_id"] != account_id:
                continue
            key = (tx["reference"], tx["amount_minor"], tx["currency"])
            if key in seen:
                duplicates.append(tx["id"])
            seen.add(key)
        return {"duplicate_ids": duplicates}

    @server.tool()
    async def get_account_balances(account_id: str, scenario: dict[str, Any]) -> dict:
        """Compute synthetic account balance using integer minor units."""
        return {
            "account_id": account_id,
            "balance_minor": sum(
                t["amount_minor"] for t in scenario.get("transactions", []) if t["account_id"] == account_id
            ),
        }

    @server.tool()
    async def search_transaction_history(query: str, account_id: str, scenario: dict[str, Any]) -> dict:
        """Search reference text within one synthetic account."""
        return {
            "transactions": [
                t
                for t in scenario.get("transactions", [])
                if t["account_id"] == account_id and query.casefold() in t["reference"].casefold()
            ]
        }

    @server.tool()
    async def assess_transaction_risk(
        transaction_id: str, amount_minor: int, threshold_minor: int, scenario: dict[str, Any]
    ) -> dict:
        """Classify synthetic high-value transactions using an explicit threshold."""
        return {
            "transaction_id": transaction_id,
            "risk": "high" if abs(amount_minor) >= threshold_minor else "low",
        }

    @server.tool()
    async def detect_transaction_anomalies(account_id: str, scenario: dict[str, Any]) -> dict:
        """Identify threshold anomalies; no claim of real fraud detection."""
        return {
            "anomaly_ids": [
                t["id"]
                for t in scenario.get("transactions", [])
                if t["account_id"] == account_id
                and abs(t["amount_minor"]) >= scenario.get("risk_threshold_minor", 100000)
            ]
        }

    @server.tool()
    async def compare_ledger_entries(account_id: str, scenario: dict[str, Any]) -> dict:
        """Compare exact synthetic bank and ledger balances."""
        return {
            "account_id": account_id,
            "difference_minor": scenario.get("bank_balance_minor", 0)
            - scenario.get("ledger_balance_minor", 0),
        }

    @server.tool()
    async def find_reconciliation_discrepancies(account_id: str, scenario: dict[str, Any]) -> dict:
        """Return synthetic evidence IDs for nonzero discrepancies."""
        delta = scenario.get("bank_balance_minor", 0) - scenario.get("ledger_balance_minor", 0)
        return {"difference_minor": delta, "evidence_ids": ["bank-1", "ledger-1"] if delta else []}

    @server.tool()
    async def generate_reconciliation_report(account_id: str, scenario: dict[str, Any]) -> dict:
        """Produce an evidence-backed synthetic report."""
        return {"account_id": account_id, "report_id": f"report-{scenario['scope']}", "simulated": True}

    @server.tool()
    async def create_approval_request(action_id: str, scenario: dict[str, Any]) -> dict:
        """Idempotently request approval; only the driver can resolve it."""
        key = f"{scenario['scope']}:{action_id}"
        approvals.setdefault(key, {"approval_id": key, "status": "pending"})
        return approvals[key]

    @server.tool()
    async def get_approval_status(approval_id: str, scenario: dict[str, Any]) -> dict:
        """Read scoped synthetic approval status."""
        if not approval_id.startswith(scenario["scope"] + ":"):
            raise ValueError("Approval scope denied")
        return approvals.get(approval_id, {"approval_id": approval_id, "status": "missing"})

    @server.tool()
    async def list_pending_approvals(scenario: dict[str, Any]) -> dict:
        """List scoped synthetic pending approvals."""
        return {
            "approvals": [
                v
                for k, v in approvals.items()
                if k.startswith(scenario["scope"] + ":") and v["status"] == "pending"
            ]
        }

    @server.tool()
    async def cancel_approval_request(approval_id: str, scenario: dict[str, Any]) -> dict:
        """Cancel only a scoped approval."""
        item = await get_approval_status(approval_id, scenario)
        if item["status"] != "pending":
            raise ValueError("Approval is not pending")
        item["status"] = "cancelled"
        return item

    @server.tool()
    async def resolve_approval(
        approval_id: str, decision: str, driver_token: str, scenario: dict[str, Any]
    ) -> dict:
        """Test driver only: simulate a human decision, never available to agents."""
        import hmac

        if not hmac.compare_digest(driver_token, os.getenv("AB_MCP_TOKEN", "local-synthetic-sandbox")):
            raise ValueError("Driver authorization denied")
        if decision not in {"approved", "rejected", "expired"}:
            raise ValueError("Invalid decision")
        item = await get_approval_status(approval_id, scenario)
        if item["status"] == "missing":
            raise ValueError("Missing approval")
        item["status"] = decision
        return item

    @server.tool()
    async def execute_correction(action_id: str, approval_id: str, scenario: dict[str, Any]) -> dict:
        """Apply at most one simulated correction, after scoped approval only."""
        key = f"{scenario['scope']}:{action_id}"
        item = await get_approval_status(approval_id, scenario)
        if approval_id != key or item["status"] != "approved":
            raise ValueError("UNAUTHORIZED: correction requires approved matching action")
        duplicate = key in executions
        executions.setdefault(key, {"action_id": action_id, "simulated": True, "executed": True})
        return {**executions[key], "duplicate_suppressed": duplicate}

    # SDK registration and discovery remain real; remove unrelated service tools.
    for name in [t.name for t in server._tool_manager.list_tools()]:
        if name not in GROUPS[group]:
            server.remove_tool(name)
    return server


class TokenMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        import hmac

        from starlette.responses import JSONResponse

        if scope["type"] == "http":
            if scope["path"] == "/health/live":
                await JSONResponse({"status": "live", "synthetic_only": True})(scope, receive, send)
                return
            headers = dict(scope.get("headers", []))
            expected = "Bearer " + os.getenv("AB_MCP_TOKEN", "local-synthetic-sandbox")
            if not hmac.compare_digest(headers.get(b"authorization", b"").decode(), expected):
                await JSONResponse({"error": "Sandbox authentication required"}, status_code=401)(
                    scope, receive, send
                )
                return
        await self.app(scope, receive, send)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("group", choices=GROUPS)
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    args = parser.parse_args()
    server = create_server(args.group)
    if args.transport == "stdio":
        server.run(transport="stdio")
    else:
        import uvicorn

        uvicorn.run(
            TokenMiddleware(server.streamable_http_app()),
            host="0.0.0.0",
            port=int(os.getenv("PORT", "8000")),
            log_level="warning",
        )


if __name__ == "__main__":
    main()
