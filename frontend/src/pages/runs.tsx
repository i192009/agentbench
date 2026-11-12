import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronDown,
  ChevronRight,
  Clock3,
  Download,
  FileCode2,
  GitBranch,
  ListTree,
  LockKeyhole,
  Play,
  Plus,
  Radio,
  ShieldCheck,
  Square,
  Terminal,
  Workflow,
  X,
} from "lucide-react";
import { api, download, followRun, post } from "../api";
import type {
  Agent,
  AgentVersion,
  CaseResult,
  Dataset,
  DatasetVersion,
  GateRow,
  Page,
  ResultRow,
  Run,
  TraceEvent,
} from "../types";
import {
  Badge,
  duration,
  Empty,
  ErrorBox,
  human,
  Json,
  Loading,
  money,
  PageIntro,
  Panel,
  percent,
  Stat,
  TableWrap,
  useApi,
} from "../ui";
import { RunTable } from "./insights";

type Go = (page: string, run?: string) => void;

export function LaunchPage({ project, go }: { project: string; go: Go }) {
  const agents = useApi<Page<Agent>>(`/projects/${project}/agents`),
    datasets = useApi<Page<Dataset>>(`/projects/${project}/datasets`),
    gates = useApi<Page<GateRow>>(`/projects/${project}/gates`);
  const [agent, setAgent] = useState(""),
    [agentVersion, setAgentVersion] = useState(""),
    [dataset, setDataset] = useState(""),
    [datasetVersion, setDatasetVersion] = useState(""),
    [mode, setMode] = useState("offline"),
    [gate, setGate] = useState(""),
    [cost, setCost] = useState(5),
    [repetitions, setRepetitions] = useState(1),
    [evaluators, setEvaluators] = useState(["deterministic"]),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const versions = useApi<Page<AgentVersion>>(
      agent ? `/projects/${project}/agents/${agent}/versions` : null,
    ),
    dataVersions = useApi<Page<DatasetVersion>>(
      dataset ? `/projects/${project}/datasets/${dataset}/versions` : null,
    );
  useEffect(() => {
    if (
      versions.data?.items.length &&
      !versions.data.items.some((v) => v.id === agentVersion)
    )
      setAgentVersion(versions.data.items[0].id);
  }, [versions.data, agentVersion]);
  useEffect(() => {
    if (
      dataVersions.data?.items.length &&
      !dataVersions.data.items.some((v) => v.id === datasetVersion)
    )
      setDatasetVersion(dataVersions.data.items[0].id);
  }, [dataVersions.data, datasetVersion]);
  const selectedVersion = versions.data?.items.find(
      (v) => v.id === agentVersion,
    ),
    config = selectedVersion?.config;
  return (
    <>
      <PageIntro
        eyebrow="TURN ASSUMPTIONS INTO EVIDENCE"
        title="Run an evaluation"
        description="Select an immutable configuration and a versioned dataset. We’ll capture the complete workflow."
      />
      <form
        className="launch-layout"
        onSubmit={async (e) => {
          e.preventDefault();
          setError("");
          setBusy(true);
          try {
            const body = {
              agent_version_id: agentVersion,
              dataset_version_id: datasetVersion,
              mode,
              max_cost_usd: cost,
              repetitions,
              evaluators,
              ...(gate
                ? {
                    gate_policy: gates.data?.items.find((g) => g.id === gate)
                      ?.policy,
                  }
                : {}),
            };
            const run = await post<Run>(`/projects/${project}/runs`, body);
            await post(`/projects/${project}/runs/${run.id}/start`);
            go("results", run.id);
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <div>
          <Panel
            title="1. Agent configuration"
            subtitle="Select exactly what you want to evaluate"
          >
            <div className="padded form-grid">
              <label>
                Agent
                <select
                  required
                  aria-label="Evaluation agent"
                  value={agent}
                  onChange={(e) => {
                    setAgent(e.target.value);
                    setAgentVersion("");
                  }}
                >
                  <option value="">Choose an agent</option>
                  {agents.data?.items.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Agent version
                <select
                  required
                  aria-label="Agent version"
                  value={agentVersion}
                  onChange={(e) => setAgentVersion(e.target.value)}
                >
                  <option value="">Select a version</option>
                  {versions.data?.items.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.version} · {String(v.config.variant)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Execution mode
                <select value={mode} onChange={(e) => setMode(e.target.value)}>
                  <option value="offline">
                    Offline deterministic / synthetic fixtures
                  </option>
                  <option value="live">
                    Live model · requires provider configuration
                  </option>
                  <option value="recorded">Recorded trace</option>
                  <option value="external">Authorized external agent</option>
                </select>
              </label>
              <label>
                Model configuration
                <div className="readonly-input">
                  {config
                    ? String(
                        (config.model as Record<string, unknown>)?.model ??
                          "Registered model",
                      )
                    : "Select an agent version"}
                </div>
              </label>
            </div>
          </Panel>
          <Panel
            title="2. Evaluation dataset"
            subtitle="Dataset versions freeze automatically when evaluated"
          >
            <div className="padded form-grid">
              <label>
                Dataset
                <select
                  required
                  aria-label="Evaluation dataset"
                  value={dataset}
                  onChange={(e) => {
                    setDataset(e.target.value);
                    setDatasetVersion("");
                  }}
                >
                  <option value="">Choose a dataset</option>
                  {datasets.data?.items.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Dataset version
                <select
                  required
                  value={datasetVersion}
                  onChange={(e) => setDatasetVersion(e.target.value)}
                >
                  <option value="">Select a version</option>
                  {dataVersions.data?.items.map((v) => (
                    <option key={v.id} value={v.id}>
                      v{v.version} ·{" "}
                      {v.frozen ? "frozen" : "draft, will freeze"}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </Panel>
          <Panel title="3. Scoring & deployment policy">
            <div className="padded">
              <div className="evaluator-options">
                {[
                  {
                    id: "deterministic",
                    name: "Deterministic invariants",
                    description:
                      "Tools, arguments, numerical facts, citations, workflow, safety and budgets",
                  },
                  {
                    id: "ragas",
                    name: "Ragas ID-based retrieval",
                    description:
                      "Official context precision and recall; no semantic judge",
                  },
                  {
                    id: "deepeval",
                    name: "DeepEval tool correctness",
                    description:
                      "Name-only comparison with model inference disabled",
                  },
                ].map((item) => (
                  <label className="checkbox-card" key={item.id}>
                    <input
                      type="checkbox"
                      disabled={item.id === "deterministic"}
                      checked={evaluators.includes(item.id)}
                      onChange={(e) =>
                        setEvaluators(
                          e.target.checked
                            ? [...evaluators, item.id]
                            : evaluators.filter((v) => v !== item.id),
                        )
                      }
                    />
                    <span>
                      <strong>{item.name}</strong>
                      <small>{item.description}</small>
                    </span>
                  </label>
                ))}
              </div>
              <label>
                Quality gate policy
                <select value={gate} onChange={(e) => setGate(e.target.value)}>
                  <option value="">Default strict policy</option>
                  {gates.data?.items.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.name}
                    </option>
                  ))}
                </select>
              </label>
              <div className="form-grid">
                <label>
                  Maximum run cost reservation ($)
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.25"
                    value={cost}
                    onChange={(e) => setCost(Number(e.target.value))}
                  />
                </label>
                <label>
                  Repetitions per case
                  <input
                    type="number"
                    min="1"
                    max="5"
                    value={repetitions}
                    onChange={(e) => setRepetitions(Number(e.target.value))}
                  />
                </label>
              </div>
            </div>
          </Panel>
          <ErrorBox error={error} />
          <button
            className="primary launch-button"
            type="submit"
            disabled={busy || !agentVersion || !datasetVersion}
          >
            <Play size={16} />
            {busy ? "Creating evaluation…" : "Start evaluation"}
            <ArrowRight size={16} />
          </button>
        </div>
        <aside>
          <Panel title="What this run records">
            <ol className="run-steps">
              <li>
                <span>01</span>
                <div>
                  <strong>Freeze the configuration</strong>
                  <p>
                    Agent, prompt, tools, dependency versions, and dataset
                    checksums.
                  </p>
                </div>
              </li>
              <li>
                <span>02</span>
                <div>
                  <strong>Execute the workflow</strong>
                  <p>
                    Real LangGraph state transitions and actual MCP tool
                    sessions.
                  </p>
                </div>
              </li>
              <li>
                <span>03</span>
                <div>
                  <strong>Evaluate the evidence</strong>
                  <p>
                    Independent assertions against outcomes and the complete
                    trajectory.
                  </p>
                </div>
              </li>
              <li>
                <span>04</span>
                <div>
                  <strong>Apply the quality gate</strong>
                  <p>
                    Explicit pass, fail, inconclusive, or error. No silent
                    substitutions.
                  </p>
                </div>
              </li>
            </ol>
          </Panel>
          <div className="info-bar">
            <ShieldCheck size={20} />
            <div>
              <strong>
                {mode === "offline"
                  ? "Offline mode is synthetic."
                  : "Configuration required."}
              </strong>
              <span>
                {mode === "offline"
                  ? "No live model reasoning is evaluated."
                  : "Missing credentials or unavailable adapters produce errors."}
              </span>
            </div>
          </div>
        </aside>
      </form>
    </>
  );
}

export function ResultsPage({
  project,
  runId,
  go,
}: {
  project: string;
  runId: string;
  go: Go;
}) {
  const client = useQueryClient(),
    runs = useApi<Page<Run>>(`/projects/${project}/runs?limit=100`, 10000),
    run = useApi<Run>(
      runId ? `/projects/${project}/runs/${runId}` : null,
      2000,
    ),
    [failed, setFailed] = useState(false),
    [offset, setOffset] = useState(0),
    [error, setError] = useState(""),
    [recentEvent, setRecentEvent] = useState("");
  const results = useApi<Page<ResultRow>>(
    runId
      ? `/projects/${project}/runs/${runId}/results?failed_only=${failed}&offset=${offset}&limit=30`
      : null,
    3000,
  );
  const active =
    !!run.data && ["CREATED", "RUNNING", "QUEUED"].includes(run.data.status);
  useEffect(() => {
    setOffset(0);
    setFailed(false);
    setRecentEvent("");
  }, [runId]);
  useEffect(() => {
    if (!runId || !active) return;
    const controller = new AbortController();
    void followRun(
      `/projects/${project}/runs/${runId}/events`,
      controller.signal,
      (name) => {
        setRecentEvent(name);
        void client.invalidateQueries({ queryKey: ["api"] });
      },
    );
    return () => controller.abort();
  }, [project, runId, active, client]);
  const detail = run.data,
    summary = detail?.summary;
  if (!runId)
    return (
      <>
        <PageIntro
          eyebrow="EVERY RUN, ACCOUNTED FOR"
          title="Evaluation results"
          description="Explore measured results, inspect failing cases, and follow the evidence into the trace."
          action={
            <button className="primary" onClick={() => go("launch")}>
              <Plus size={16} />
              New evaluation
            </button>
          }
        />
        <ErrorBox error={runs.error} />
        <Panel
          title="Evaluation history"
          subtitle={`${runs.data?.total ?? 0} persisted runs`}
        >
          {runs.isLoading ? (
            <Loading />
          ) : (
            <RunTable runs={runs.data?.items ?? []} go={go} />
          )}
        </Panel>
      </>
    );
  return (
    <>
      <button className="back-link" onClick={() => go("results")}>
        <ArrowLeft size={14} />
        All evaluation runs
      </button>
      <PageIntro
        eyebrow={`RUN ${runId.slice(0, 8).toUpperCase()}`}
        title={detail?.snapshot?.agent.name ?? "Evaluation run"}
        description={`${detail?.snapshot?.agent.version ?? ""} · ${detail?.snapshot?.dataset.name ?? ""} · ${detail?.snapshot?.request.mode ?? ""}`}
        action={
          <div className="button-group">
            <button className="secondary" onClick={() => go("traces", runId)}>
              <Workflow size={15} />
              Explore traces
            </button>
            <button
              className="secondary"
              onClick={() =>
                void download(
                  `/projects/${project}/runs/${runId}/export`,
                  "evaluation.json",
                ).catch((e) => setError(e.message))
              }
            >
              <Download size={15} />
              Export
            </button>
          </div>
        }
      />
      <ErrorBox error={error || run.error || detail?.error} />
      {detail && (
        <>
          <div className="run-status-bar">
            <Badge value={detail.status} />
            <span>
              {detail.completed} / {detail.total} cases completed
            </span>
            <span className="muted mono">{recentEvent}</span>
            {active ? (
              <button
                className="danger-button"
                onClick={async () => {
                  await post(`/projects/${project}/runs/${runId}/cancel`);
                  void client.invalidateQueries();
                }}
              >
                <Square size={12} />
                Cancel run
              </button>
            ) : (
              summary?.gate?.status === "PASS" && (
                <button
                  className="secondary small-button"
                  onClick={() =>
                    void post(`/projects/${project}/runs/${runId}/baseline`)
                      .then(() => setRecentEvent("Baseline pinned"))
                      .catch((e) => setError(e.message))
                  }
                >
                  <GitBranch size={14} />
                  Pin baseline
                </button>
              )
            )}
          </div>
          <div className="progress-track">
            <span
              style={{
                width: `${detail.total ? (detail.completed / detail.total) * 100 : 0}%`,
              }}
            />
          </div>
        </>
      )}
      {summary?.gate && (
        <div
          className={
            "gate-banner " +
            (summary.gate.status === "PASS" ? "passing" : "failing")
          }
        >
          <ShieldCheck size={22} />
          <div>
            <strong>Quality gate: {summary.gate.status}</strong>
            <p>
              {[...summary.gate.failures, ...summary.gate.inconclusive].join(
                " · ",
              ) ||
                "All configured safety, quality, completeness, and budget checks passed."}
            </p>
          </div>
          <Badge value={summary.gate.status} />
        </div>
      )}
      <div className="stats-grid">
        <Stat
          label="Task success"
          value={percent(summary?.success_rate)}
          tone="green"
        />
        <Stat label="Failed cases" value={summary?.failed ?? "—"} />
        <Stat
          label="Mean execution latency"
          value={duration(summary?.average_latency_ms)}
        />
        <Stat
          label="Estimated provider cost"
          value={money(summary?.average_cost_usd)}
        />
      </div>
      {summary?.metrics && (
        <Panel
          title="Evaluation scorecard"
          subtitle="Every score links to per-case evaluation evidence"
        >
          <div className="scorecard">
            {Object.entries(summary.metrics).map(([name, value]) => (
              <div key={name}>
                <span>{human(name)}</span>
                <strong className={value < 0.9 ? "text-danger" : "mint"}>
                  {percent(value)}
                </strong>
                <div className="score-track">
                  <i
                    style={{
                      width: value * 100 + "%",
                      background: value < 0.9 ? "#ef8f92" : "#91edb8",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Panel>
      )}
      <Panel
        title="Test case results"
        subtitle="Open a case to inspect its execution and assertion evidence"
        action={
          <label className="switch">
            <input
              type="checkbox"
              checked={failed}
              onChange={(e) => {
                setFailed(e.target.checked);
                setOffset(0);
              }}
            />
            Failed cases only
          </label>
        }
      >
        <TableWrap>
          <table>
            <thead>
              <tr>
                <th>Case</th>
                <th>Outcome</th>
                <th>State</th>
                <th>Tool calls</th>
                <th>Latency</th>
                <th>Findings</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {results.data?.items.map((row) => (
                <tr
                  key={row.id}
                  className="clickable"
                  onClick={() => {
                    sessionStorage.setItem("trace-case", row.case_id);
                    go("traces", runId);
                  }}
                >
                  <td className="mono">{row.case_id}</td>
                  <td>
                    <Badge value={row.passed ? "PASS" : "FAIL"} />
                  </td>
                  <td>{human(row.body.execution.final_state)}</td>
                  <td className="mono">
                    {row.body.execution.tool_calls.length}
                  </td>
                  <td className="mono">
                    {duration(row.body.execution.latency_ms)}
                  </td>
                  <td>
                    <span className="muted">
                      {row.body.metrics
                        .filter(
                          (m) => !["PASS", "NOT_APPLICABLE"].includes(m.status),
                        )
                        .map((m) => human(m.name))
                        .join(", ") || "All assertions passed"}
                    </span>
                  </td>
                  <td>
                    <ChevronRight size={15} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
        {!results.data?.total && (
          <Empty
            title={
              active
                ? "Evaluation in progress"
                : failed
                  ? "No failed cases"
                  : "No case results yet"
            }
          />
        )}
        <div className="pagination">
          <span>{results.data?.total ?? 0} results</span>
          <div>
            <button
              className="secondary small-button"
              disabled={!offset}
              onClick={() => setOffset(offset - 30)}
            >
              Previous
            </button>
            <button
              className="secondary small-button"
              disabled={offset + 30 >= (results.data?.total ?? 0)}
              onClick={() => setOffset(offset + 30)}
            >
              Next
            </button>
          </div>
        </div>
      </Panel>
      {summary?.tracking && (
        <div className="tracking-note">
          <Activity size={16} />
          MLflow: <Badge value={summary.tracking.status} />
          {summary.tracking.run_id && <code>{summary.tracking.run_id}</code>}
          {summary.tracking.reason && (
            <span className="muted">{summary.tracking.reason}</span>
          )}
        </div>
      )}
    </>
  );
}

export function TracesPage({
  project,
  runId,
}: {
  project: string;
  runId: string;
}) {
  const runs = useApi<Page<Run>>(`/projects/${project}/runs?limit=100`),
    [selectedRun, setSelectedRun] = useState(runId),
    [caseId, setCaseId] = useState(sessionStorage.getItem("trace-case") ?? ""),
    [selectedEvent, setSelectedEvent] = useState<TraceEvent | null>(null),
    [tab, setTab] = useState("timeline");
  useEffect(() => {
    setSelectedRun(runId);
  }, [runId]);
  const cases = useApi<Page<ResultRow>>(
    selectedRun
      ? `/projects/${project}/runs/${selectedRun}/results?limit=100`
      : null,
  );
  useEffect(() => {
    if (
      cases.data?.items.length &&
      !cases.data.items.find((c) => c.case_id === caseId)
    )
      setCaseId(cases.data.items[0].case_id);
  }, [cases.data, caseId]);
  const trace = useApi<CaseResult>(
    selectedRun && caseId
      ? `/projects/${project}/runs/${selectedRun}/results/${caseId}/trace`
      : null,
  );
  useEffect(() => setSelectedEvent(null), [caseId, selectedRun]);
  const result = trace.data,
    execution = result?.execution,
    failures =
      result?.metrics.filter(
        (m) => !["PASS", "NOT_APPLICABLE"].includes(m.status),
      ) ?? [];
  return (
    <>
      <PageIntro
        eyebrow="THE WORKFLOW IS THE EVIDENCE"
        title="Agent trace explorer"
        description="Follow graph transitions, inspect tool arguments, and see exactly where an assertion failed."
      />
      <Panel>
        <div className="trace-selectors">
          <label>
            Evaluation run
            <select
              value={selectedRun}
              onChange={(e) => setSelectedRun(e.target.value)}
            >
              <option value="">Select an evaluation</option>
              {runs.data?.items.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.agent} {r.version} · {r.dataset} · {r.id.slice(0, 8)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Test case
            <select
              aria-label="Trace test case"
              value={caseId}
              onChange={(e) => setCaseId(e.target.value)}
            >
              <option value="">Select a case</option>
              {cases.data?.items.map((c) => (
                <option key={c.id} value={c.case_id}>
                  {c.case_id} · {c.passed ? "PASS" : "FAIL"}
                </option>
              ))}
            </select>
          </label>
        </div>
      </Panel>
      <ErrorBox error={trace.error} />
      {result && execution ? (
        <>
          <div className="trace-summary">
            <div>
              <Badge value={result.passed ? "PASS" : "FAIL"} />
              <code>{caseId}</code>
              <span>{execution.trace.length} events</span>
              <span>{execution.tool_calls.length} tool calls</span>
              <span>{duration(execution.latency_ms)}</span>
            </div>
            <span className="subtle-chip">
              {execution.mode} · {execution.final_state}
            </span>
          </div>
          {failures.length > 0 && (
            <div className="trace-findings">
              {failures.map((m) => (
                <details key={m.name} open={m.name === "safety"}>
                  <summary>
                    <Badge value={m.status} />
                    <strong>{human(m.name)}</strong>
                    <span>{m.reason}</span>
                  </summary>
                  <Json value={m.evidence} />
                </details>
              ))}
            </div>
          )}
          <div className="tabs" role="tablist">
            {["timeline", "tools", "evidence", "output"].map((t) => (
              <button
                role="tab"
                aria-selected={tab === t}
                className={tab === t ? "active-tab" : ""}
                key={t}
                onClick={() => setTab(t)}
              >
                {human(t)}
                {t === "tools" && <span>{execution.tool_calls.length}</span>}
              </button>
            ))}
          </div>
          {tab === "timeline" && (
            <div className="trace-layout">
              <Panel
                title="Execution trajectory"
                subtitle="Normalized events from the complete workflow"
              >
                <ol className="timeline">
                  {execution.trace.map((event, index) => {
                    const error = ["ErrorOccurred", "BudgetExceeded"].includes(
                        event.event,
                      ),
                      approval = event.event.startsWith("HumanApproval");
                    return (
                      <li
                        className={
                          (error
                            ? "trace-error "
                            : approval
                              ? "trace-approval "
                              : "") +
                          (selectedEvent?.id === event.id
                            ? "trace-selected"
                            : "")
                        }
                        key={event.id}
                      >
                        <button onClick={() => setSelectedEvent(event)}>
                          <span className="event-index">
                            {String(index + 1).padStart(2, "0")}
                          </span>
                          <span className="event-dot">
                            {error ? (
                              <X size={12} />
                            ) : approval ? (
                              <ShieldCheck size={12} />
                            ) : event.event.startsWith("Tool") ? (
                              <Terminal size={12} />
                            ) : (
                              <GitBranch size={12} />
                            )}
                          </span>
                          <div>
                            <strong>{human(event.event)}</strong>
                            <small>
                              {event.node ||
                                String(
                                  event.data.tool ??
                                    event.data.status ??
                                    "agent",
                                )}
                            </small>
                          </div>
                          {event.data.tool != null && (
                            <code>{String(event.data.tool)}</code>
                          )}
                          <span className="event-duration">
                            {event.duration_ms > 0
                              ? duration(event.duration_ms)
                              : ""}
                          </span>
                          <ChevronRight size={14} />
                        </button>
                      </li>
                    );
                  })}
                </ol>
              </Panel>
              <Panel
                title={
                  selectedEvent ? human(selectedEvent.event) : "Event inspector"
                }
                subtitle={selectedEvent?.timestamp}
              >
                {selectedEvent ? (
                  <div className="padded">
                    <div className="config-labels">
                      <span>Node: {selectedEvent.node || "agent"}</span>
                      <span>
                        Duration: {duration(selectedEvent.duration_ms)}
                      </span>
                    </div>
                    <Json value={selectedEvent.data} />
                    <p className="muted mono">Event {selectedEvent.id}</p>
                  </div>
                ) : (
                  <Empty title="Select a trace event">
                    Inspect the exact arguments, returned evidence, state
                    transition, or error.
                  </Empty>
                )}
              </Panel>
            </div>
          )}
          {tab === "tools" && (
            <Panel
              title="MCP tool calls"
              subtitle="Arguments and results captured at the protocol boundary"
            >
              {execution.tool_calls.map((call, i) => (
                <details className="tool-detail" key={i}>
                  <summary>
                    <Terminal size={16} />
                    <strong>{call.name}</strong>
                    <Badge value={call.status} />
                    <span className="muted mono">
                      {duration(call.duration_ms)}
                    </span>
                  </summary>
                  <div className="two-col padded">
                    <div>
                      <h3>Arguments</h3>
                      <Json value={call.arguments} />
                    </div>
                    <div>
                      <h3>Result</h3>
                      <Json value={call.result} />
                    </div>
                  </div>
                </details>
              ))}
            </Panel>
          )}
          {tab === "evidence" && (
            <div className="two-col">
              <Panel title="Retrieved sources">
                {execution.documents.length ? (
                  execution.documents.map((d) => (
                    <div className="evidence-card" key={d.id}>
                      <h3>
                        <FileCode2 size={16} />
                        {d.id}
                        <span className="subtle-chip">v{d.version}</span>
                      </h3>
                      <p>{d.content}</p>
                      <Json value={d.facts} />
                    </div>
                  ))
                ) : (
                  <Empty title="No retrieved documents" />
                )}
              </Panel>
              <Panel title="Claim-attached citations">
                <div className="padded">
                  <Json value={execution.citations} />
                  <p className="muted">
                    Source identity and exact quotes are checked separately from
                    structured fact support. Valid IDs alone do not establish
                    semantic entailment.
                  </p>
                </div>
              </Panel>
            </div>
          )}
          {tab === "output" && (
            <Panel title="Final execution result">
              <div className="padded">
                <Json value={execution.output} />
                {execution.errors.length > 0 && (
                  <ErrorBox error={execution.errors.join("; ")} />
                )}
                <h3>Evaluation evidence</h3>
                {result.metrics.map((m) => (
                  <details key={m.name}>
                    <summary>
                      <Badge value={m.status} />
                      {human(m.name)}
                      <span className="muted">
                        {m.score == null ? "—" : percent(m.score)}
                      </span>
                    </summary>
                    <p>{m.reason}</p>
                    <Json value={m.evidence} />
                  </details>
                ))}
              </div>
            </Panel>
          )}
        </>
      ) : trace.isFetching ? (
        <Loading />
      ) : (
        <Empty title="Follow an agent from request to outcome">
          Select a persisted run and test case to explore its actual execution
          trace.
        </Empty>
      )}
    </>
  );
}
