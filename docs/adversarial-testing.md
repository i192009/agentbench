# Adversarial evaluation

Thirty curated attacks cover document/tool-output injection, system/developer spoofing,
privilege escalation, exfiltration requests, citation poisoning, schema poisoning, urgency,
benchmark/reward manipulation, approval bypass, duplicate operations and audit evasion.
All values, issuers, accounts, transactions and destinations are synthetic.

The deterministic baseline treats retrieved content as evidence and ignores instructions
inside it. A deliberately vulnerable test variant attempts a forbidden tool when it sees
injected output. The executor records and blocks the attempt. The scorer still fails safety;
a harmless final answer cannot erase the trajectory violation.

The deliberately broken operations variant calls the simulated correction before approval.
The approval service rejects it independently. Tests also cover rejection, expiry, pending
interrupts, approved resume, action scope and duplicate suppression. An optional fixture
`protected_values` list detects synthetic canary disclosure in output or outgoing arguments.

The sandbox has no payment, secret-export, command-execution or arbitrary-fetch implementation.
Forbidden tools remain observable attempted calls, not successful side effects. Ragas and
DeepEval usage telemetry is disabled, and model-provider credentials are isolated from
sandbox processes/containers.

Offline containment tests evaluate the implemented rules and workflow. They do not establish
the resistance of a live LLM or a production application. A live attack campaign must use
explicitly configured sandbox instances and credentials; no such campaign was run here.
