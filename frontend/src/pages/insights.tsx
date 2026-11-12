import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronRight,
  Clock3,
  FlaskConical,
  GitCompareArrows,
  Plus,
  ShieldAlert,
  ShieldCheck,
  Zap,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, post } from "../api";
import type {
  Agent,
  Analytics,
  Comparison,
  GateRow,
  Page,
  Run,
} from "../types";
import {
  Badge,
  duration,
  Empty,
  ErrorBox,
  human,
  Json,
  Loading,
  Modal,
  money,
  PageIntro,
  Panel,
  percent,
  Stat,
  TableWrap,
  TextLink,
  useApi,
} from "../ui";

type Go = (page: string, run?: string) => void;
const chartTheme = {
  background: "#131b25",
  border: "1px solid #293341",
  borderRadius: 8,
  color: "#d7dfeb",
  fontSize: 12,
};

export function RunTable({ runs, go }: { runs: Run[]; go: Go }) {
  if (!runs.length)
    return (
      <Empty title="No evaluation runs yet">
        Start an evaluation to see measured results and deployment decisions.
      </Empty>
    );
  return (
    <TableWrap>
      <table>
        <thead>
          <tr>
            <th>Evaluation / agent</th>
            <th>Dataset</th>
            <th>Success rate</th>
            <th>Duration / case</th>
            <th>Quality gate</th>
            <th>Started</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr
              key={run.id}
              onClick={() => go("results", run.id)}
              className="clickable"
            >
              <td>
                <div className="table-title">
                  <span className="run-icon">
                    <FlaskConical size={15} />
                  </span>
                  <div>
                    <strong>{run.agent || run.snapshot?.agent.name}</strong>
                    <small>
                      <code>{run.id.slice(0, 8)}</code>
                      <span className="version-tag">
                        {run.version || run.snapshot?.agent.version}
                      </span>
                    </small>
                  </div>
                </div>
              </td>
              <td>
                <span className="dataset-label">
                  {run.dataset || run.snapshot?.dataset.name}
                </span>
                <small className="cell-sub">
                  {run.summary.count ?? run.completed} cases ·{" "}
                  {run.mode || run.snapshot?.request.mode}
                </small>
              </td>
              <td>
                <span
                  className={
                    (run.summary.success_rate ?? 0) < 0.9
                      ? "text-danger"
                      : "mint"
                  }
                >
                  {percent(run.summary.success_rate)}
                </span>
              </td>
              <td className="mono">
                {duration(run.summary.average_latency_ms)}
              </td>
              <td>
                <Badge value={run.summary.gate?.status ?? run.status} />
              </td>
              <td className="muted">
                {new Date(run.created_at).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </td>
              <td>
                <ChevronRight size={15} className="muted" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </TableWrap>
  );
}

export function Overview({ project, go }: { project: string; go: Go }) {
  const analytics = useApi<Analytics>(`/projects/${project}/analytics`, 10000),
    runs = useApi<Page<Run>>(`/projects/${project}/runs?limit=6`, 10000),
    agents = useApi<Page<Agent>>(`/projects/${project}/agents`);
  const data = analytics.data?.runs ?? [],
    completed = data.filter((r) => r.summary.count),
    caseCount = completed.reduce((n, r) => n + (r.summary.count ?? 0), 0),
    passed = completed.reduce((n, r) => n + (r.summary.passed ?? 0), 0),
    failed = caseCount - passed,
    safety = completed.reduce(
      (n, r) => n + (r.summary.safety_violations ?? 0),
      0,
    );
  const timeline = [...completed]
    .reverse()
    .map((r, i) => ({
      name: `#${i + 1}`,
      success: (r.summary.success_rate ?? 0) * 100,
      label: r.agent + " " + r.version,
      latency: r.summary.average_latency_ms ?? 0,
    }));
  const goodGates = completed.filter(
    (r) => r.summary.gate?.status === "PASS",
  ).length;
  return (
    <>
      <PageIntro
        eyebrow="AGENT RELIABILITY, AT A GLANCE"
        title="Evaluation overview"
        description="A clear view of how your agents perform, where they fail, and what changed."
        action={
          <button className="primary" onClick={() => go("launch")}>
            <Plus size={16} />
            New evaluation
          </button>
        }
      />
      <div className="overview-banner">
        <span className="banner-icon">
          <ShieldCheck size={21} />
        </span>
        <div>
          <strong>Your next deployment starts with evidence.</strong>
          <p>
            Evaluate the complete agent workflow — tools, sources, decisions,
            and outcomes.
          </p>
        </div>
        <button onClick={() => go("gates")}>
          View quality gates
          <ArrowRight size={15} />
        </button>
      </div>
      <div className="stats-grid">
        <Stat
          label="Evaluation runs"
          value={analytics.data?.total_runs ?? "—"}
          detail={`${caseCount} cases evaluated in current window`}
          icon={<FlaskConical size={16} />}
        />
        <Stat
          label="Task success rate"
          value={caseCount ? percent(passed / caseCount) : "—"}
          detail={`${failed} cases need investigation`}
          icon={<Activity size={16} />}
          tone="green"
        />
        <Stat
          label="Registered agents"
          value={agents.data?.total ?? "—"}
          detail="Versioned configurations & prompts"
          icon={<Zap size={16} />}
        />
        <Stat
          label="Safety findings"
          value={safety}
          detail={
            safety
              ? "Unsafe attempts detected and recorded"
              : "No recorded violations in current window"
          }
          icon={<ShieldAlert size={16} />}
          tone={safety ? "red" : ""}
        />
      </div>
      <ErrorBox error={analytics.error} />
      <div className="chart-grid">
        <Panel
          title="Quality over time"
          subtitle="Measured task success across completed evaluations"
          action={<span className="subtle-chip">Latest 100 runs</span>}
        >
          <div className="chart-legend">
            <span>
              <i className="legend-dot" />
              Task success
            </span>
            <span className="muted">Higher is better</span>
          </div>
          <div className="chart">
            {timeline.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={timeline}
                  margin={{ top: 12, right: 20, left: -15, bottom: 0 }}
                >
                  <defs>
                    <linearGradient
                      id="successFill"
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop offset="0%" stopColor="#91edb8" stopOpacity={0.2} />
                      <stop offset="100%" stopColor="#91edb8" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid
                    stroke="#202a35"
                    strokeDasharray="3 5"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="name"
                    stroke="#738092"
                    tickLine={false}
                    axisLine={false}
                    fontSize={11}
                  />
                  <YAxis
                    domain={[0, 100]}
                    tickFormatter={(v) => v + "%"}
                    stroke="#738092"
                    tickLine={false}
                    axisLine={false}
                    fontSize={11}
                  />
                  <Tooltip
                    contentStyle={chartTheme}
                    formatter={(v) => [
                      Number(v).toFixed(1) + "%",
                      "Task success",
                    ]}
                  />
                  <Area
                    type="monotone"
                    dataKey="success"
                    stroke="#91edb8"
                    strokeWidth={2}
                    fill="url(#successFill)"
                    dot={{
                      r: 3,
                      fill: "#91edb8",
                      stroke: "#0d141b",
                      strokeWidth: 2,
                    }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <Empty title="Your first data point is one run away" />
            )}
          </div>
        </Panel>
        <Panel
          title="Deployment signals"
          subtitle="Decisions backed by evaluated outcomes"
        >
          <div className="signal-score">
            <div className="signal-number">
              {goodGates}
              <span> / {completed.length}</span>
            </div>
            <span className="muted">completed runs passed their gate</span>
          </div>
          <div className="signal-row">
            <span className="signal-icon good">
              <Check size={15} />
            </span>
            <div>
              <strong>Passing quality gates</strong>
              <small>All configured checks satisfied</small>
            </div>
            <b>{goodGates}</b>
          </div>
          <div className="signal-row">
            <span className="signal-icon bad">
              <ShieldAlert size={15} />
            </span>
            <div>
              <strong>Blocked evaluations</strong>
              <small>Failing, inconclusive, or error gates</small>
            </div>
            <b>{completed.length - goodGates}</b>
          </div>
          <div className="signal-row">
            <span className="signal-icon blue">
              <Activity size={15} />
            </span>
            <div>
              <strong>In progress</strong>
              <small>Queued or running evaluations</small>
            </div>
            <b>
              {
                data.filter((r) => ["RUNNING", "QUEUED"].includes(r.status))
                  .length
              }
            </b>
          </div>
          <div className="signal-note">
            <ShieldCheck size={14} />
            Unsafe attempts fail safety checks, even when blocked.
          </div>
        </Panel>
      </div>
      <Panel
        title="Recent evaluations"
        subtitle="Reproducible runs with immutable agent and dataset snapshots"
        action={
          <TextLink onClick={() => go("results")}>View all runs</TextLink>
        }
      >
        {runs.isLoading ? (
          <Loading />
        ) : (
          <RunTable runs={runs.data?.items ?? []} go={go} />
        )}
      </Panel>
      <div className="quick-grid">
        <button className="quick-card" onClick={() => go("traces")}>
          <span className="quick-icon">
            <Activity size={20} />
          </span>
          <div>
            <strong>Follow every decision</strong>
            <p>Inspect tools, evidence, and graph transitions.</p>
          </div>
          <ArrowUpRight size={18} />
        </button>
        <button className="quick-card" onClick={() => go("comparison")}>
          <span className="quick-icon purple">
            <GitCompareArrows size={20} />
          </span>
          <div>
            <strong>Find what changed</strong>
            <p>Compare versions with paired regression analysis.</p>
          </div>
          <ArrowUpRight size={18} />
        </button>
      </div>
    </>
  );
}

export function ComparisonPage({ project }: { project: string }) {
  const runs = useApi<Page<Run>>(`/projects/${project}/runs?limit=100`),
    [baseline, setBaseline] = useState(""),
    [candidate, setCandidate] = useState(""),
    [submitted, setSubmitted] = useState<{ a: string; b: string } | null>(null);
  const result = useApi<Comparison>(
    submitted
      ? `/projects/${project}/comparisons?baseline_id=${submitted.a}&candidate_id=${submitted.b}`
      : null,
  );
  const completed =
    runs.data?.items.filter((r) =>
      ["COMPLETED", "COMPLETED_WITH_ERRORS"].includes(r.status),
    ) ?? [];
  return (
    <>
      <PageIntro
        eyebrow="CHANGE WITH CONFIDENCE"
        title="Regression comparison"
        description="Pair identical test cases to separate observed changes from statistical uncertainty."
      />
      <Panel title="Choose two evaluation runs">
        <form
          className="inline-form padded"
          onSubmit={(e) => {
            e.preventDefault();
            setSubmitted({ a: baseline, b: candidate });
          }}
        >
          <label>
            Baseline run
            <select
              required
              value={baseline}
              onChange={(e) => setBaseline(e.target.value)}
            >
              <option value="">Select baseline</option>
              {completed.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.agent} {r.version} · {r.dataset} · {r.id.slice(0, 8)}
                </option>
              ))}
            </select>
          </label>
          <GitCompareArrows className="muted" size={20} />
          <label>
            Candidate run
            <select
              required
              value={candidate}
              onChange={(e) => setCandidate(e.target.value)}
            >
              <option value="">Select candidate</option>
              {completed
                .filter((r) => r.id !== baseline)
                .map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.agent} {r.version} · {r.dataset} · {r.id.slice(0, 8)}
                  </option>
                ))}
            </select>
          </label>
          <button className="primary">
            Compare runs
            <ArrowRight size={15} />
          </button>
        </form>
      </Panel>
      <ErrorBox error={result.error} />
      {result.isFetching ? (
        <Loading />
      ) : result.data ? (
        <>
          <div className="stats-grid">
            <Stat label="Paired cases" value={result.data.paired_count} />
            <Stat
              label="Task success delta"
              value={percent(result.data.effect_size)}
              tone={result.data.effect_size < 0 ? "red" : "green"}
            />
            <Stat
              label="New failures"
              value={result.data.new_failures.length}
            />
            <Stat
              label="Recovered cases"
              value={result.data.recovered.length}
            />
          </div>
          <Panel
            title="Statistical assessment"
            action={
              <Badge
                value={
                  result.data.statistical_regression
                    ? "FAIL"
                    : result.data.status
                }
              />
            }
          >
            <div className="padded">
              <p>
                95% paired bootstrap interval:{" "}
                <code>{result.data.delta_ci95.map(percent).join(" to ")}</code>.{" "}
                {result.data.statistical_regression
                  ? "A statistically supported regression was detected."
                  : "See the interval and sample size before interpreting this change."}
              </p>
              <p className="muted">
                Case-level bootstrap · fixed seed · repeated evaluations
                clustered by case · not a guarantee of future behavior.
              </p>
            </div>
          </Panel>
          <Panel title="Metric differences">
            <TableWrap>
              <table>
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Baseline</th>
                    <th>Candidate</th>
                    <th>Delta</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(result.data.metric_deltas).map(
                    ([name, delta]) => (
                      <tr key={name}>
                        <td>{human(name)}</td>
                        <td className="mono">
                          {percent(result.data!.baseline.metrics?.[name])}
                        </td>
                        <td className="mono">
                          {percent(result.data!.candidate.metrics?.[name])}
                        </td>
                        <td className={delta < 0 ? "text-danger" : "mint"}>
                          {delta > 0 ? "+" : ""}
                          {percent(delta)}
                        </td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </TableWrap>
          </Panel>
          <div className="two-col">
            <Panel title="Newly failing cases">
              {result.data.new_failures.length ? (
                <div className="padded case-chips">
                  {result.data.new_failures.map((id) => (
                    <code key={id} className="case-chip bad">
                      {id}
                    </code>
                  ))}
                </div>
              ) : (
                <Empty title="No new failures" />
              )}
            </Panel>
            <Panel title="Trajectory changes">
              {result.data.trajectory_changes.length ? (
                <div className="padded">
                  {result.data.trajectory_changes.map((item) => (
                    <details key={item.case_id}>
                      <summary>{item.case_id}</summary>
                      <Json value={item} />
                    </details>
                  ))}
                </div>
              ) : (
                <Empty title="No tool sequence changes" />
              )}
            </Panel>
          </div>
        </>
      ) : (
        <Empty title="Compare the evidence behind two versions">
          Select completed runs that used the same frozen dataset.
        </Empty>
      )}
    </>
  );
}

export function GatesPage({ project }: { project: string }) {
  const policies = useApi<Page<GateRow>>(`/projects/${project}/gates`),
    runs = useApi<Page<Run>>(`/projects/${project}/runs?limit=30`),
    [editing, setEditing] = useState<GateRow | null>(null),
    [text, setText] = useState(""),
    [name, setName] = useState(""),
    [error, setError] = useState(""),
    client = useQueryClient();
  const save = useMutation({
    mutationFn: async () => {
      const policy = JSON.parse(text);
      if (editing?.id)
        return api(`/projects/${project}/gates/${editing.id}`, {
          method: "PUT",
          body: JSON.stringify({ name, policy }),
        });
      return post(`/projects/${project}/gates`, { name, policy });
    },
    onSuccess: () => {
      setEditing(null);
      void client.invalidateQueries();
    },
    onError: (e) => setError(e.message),
  });
  function edit(row: GateRow) {
    setEditing(row);
    setText(JSON.stringify(row.policy, null, 2));
    setName(row.name);
    setError("");
  }
  return (
    <>
      <PageIntro
        eyebrow="RELEASE CRITERIA, EXPLICIT"
        title="CI/CD quality gates"
        description="Hard safety invariants, quality thresholds, regression limits, and budget checks."
        action={
          <button
            className="primary"
            onClick={() =>
              edit({
                id: "",
                name: "New policy",
                policy: {
                  minimum_success: 0.9,
                  minimum_tool_correctness: 0.95,
                  minimum_citation_validity: 0.98,
                  maximum_safety_violations: 0,
                  minimum_sample_size: 10,
                },
              })
            }
          >
            <Plus size={16} />
            New policy
          </button>
        }
      />
      <div className="info-bar">
        <ShieldCheck size={18} />
        <div>
          <strong>Missing evidence never becomes a passing gate.</strong>
          <span>PASS exits 0 · FAIL exits 1 · INCONCLUSIVE exits 2</span>
        </div>
      </div>
      <div className="policy-grid">
        {policies.data?.items.map((row) => (
          <Panel
            key={row.id}
            title={row.name}
            action={
              <button
                className="secondary small-button"
                onClick={() => edit(row)}
              >
                Edit policy
              </button>
            }
          >
            <div className="padded policy-values">
              {Object.entries(row.policy).map(([k, v]) => (
                <div key={k}>
                  <span>{human(k)}</span>
                  <code>
                    {typeof v === "object" ? JSON.stringify(v) : String(v)}
                  </code>
                </div>
              ))}
            </div>
          </Panel>
        ))}
      </div>
      <ErrorBox error={policies.error} />
      <Panel
        title="Latest gate decisions"
        subtitle="Policies are frozen into each run; editing a policy does not rewrite history"
      >
        <TableWrap>
          <table>
            <thead>
              <tr>
                <th>Run</th>
                <th>Version</th>
                <th>Gate</th>
                <th>Evidence</th>
              </tr>
            </thead>
            <tbody>
              {runs.data?.items
                .filter((r) => r.summary.gate)
                .map((r) => (
                  <tr key={r.id}>
                    <td>
                      <strong>{r.agent}</strong>
                      <small className="cell-sub mono">
                        {r.id.slice(0, 8)}
                      </small>
                    </td>
                    <td>{r.version}</td>
                    <td>
                      <Badge value={r.summary.gate!.status} />
                    </td>
                    <td className="muted">
                      {[
                        ...r.summary.gate!.failures,
                        ...r.summary.gate!.inconclusive,
                      ].join("; ") || "All configured requirements satisfied"}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </TableWrap>
      </Panel>
      {editing && (
        <Modal title="Quality gate policy" close={() => setEditing(null)}>
          <form
            className="padded"
            onSubmit={(e) => {
              e.preventDefault();
              save.mutate();
            }}
          >
            <label>
              Policy name
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </label>
            <label>
              Policy configuration
              <textarea
                className="code-editor"
                rows={18}
                value={text}
                onChange={(e) => setText(e.target.value)}
              />
            </label>
            <ErrorBox error={error} />
            <button className="primary" disabled={save.isPending}>
              Save policy
            </button>
          </form>
        </Modal>
      )}
    </>
  );
}

export function AdversarialPage({ project, go }: { project: string; go: Go }) {
  const runs = useApi<Page<Run>>(`/projects/${project}/runs?limit=100`),
    attacks =
      runs.data?.items.filter(
        (r) =>
          r.dataset === "adversarial" || (r.summary.safety_violations ?? 0) > 0,
      ) ?? [];
  const findings = attacks.reduce(
    (n, r) => n + (r.summary.safety_violations ?? 0),
    0,
  );
  return (
    <>
      <PageIntro
        eyebrow="TEST THE TRUST BOUNDARY"
        title="Adversarial testing"
        description="Inspect tool-output injection, privilege escalation, exfiltration, and approval bypass attempts."
        action={
          <button className="primary" onClick={() => go("launch")}>
            <Plus size={16} />
            Run safety evaluation
          </button>
        }
      />
      <div className="stats-grid">
        <Stat label="Safety evaluations" value={attacks.length} />
        <Stat
          label="Cases evaluated"
          value={attacks.reduce((n, r) => n + (r.summary.count ?? 0), 0)}
        />
        <Stat
          label="Unsafe attempts"
          value={findings}
          tone={findings ? "red" : "green"}
        />
        <Stat
          label="Fixture isolation"
          value="Synthetic"
          detail="No real credentials or financial operations"
        />
      </div>
      <Panel
        title="Attack findings"
        subtitle="A blocked unsafe attempt remains a failed safety result"
      >
        <RunTable runs={attacks} go={go} />
      </Panel>
      <div className="two-col">
        <Panel title="Trust boundaries tested">
          <ul className="feature-list">
            <li>
              <ShieldCheck size={17} />
              Retrieved documents are evidence, not instructions
            </li>
            <li>
              <ShieldCheck size={17} />
              Tool output cannot grant new permissions
            </li>
            <li>
              <ShieldCheck size={17} />
              Corrections require matching approval
            </li>
            <li>
              <ShieldCheck size={17} />
              Duplicate operations are suppressed
            </li>
          </ul>
        </Panel>
        <Panel title="Reading the results">
          <div className="padded muted">
            <p>
              Offline tests measure the implemented deterministic policy and
              workflow. They do not establish a live language model’s resistance
              to prompt injection.
            </p>
            <p>
              Open a failed case to inspect the exact attempted tool call and
              the safety evaluator’s evidence.
            </p>
          </div>
        </Panel>
      </div>
    </>
  );
}

export function AnalyticsPage({ project }: { project: string }) {
  const result = useApi<Analytics>(`/projects/${project}/analytics`),
    rows = result.data?.runs.filter((r) => r.summary.count) ?? [];
  const points = rows
    .filter((r) => r.summary.average_cost_usd != null)
    .map((r) => ({
      cost: r.summary.average_cost_usd,
      quality: (r.summary.success_rate ?? 0) * 100,
      name: r.agent + " " + r.version,
    }));
  const latency = rows.map((r) => ({
    latency: r.summary.average_latency_ms,
    quality: (r.summary.success_rate ?? 0) * 100,
    name: r.agent + " " + r.version,
  }));
  return (
    <>
      <PageIntro
        eyebrow="MAKE THE TRADEOFFS VISIBLE"
        title="Experiment analytics"
        description="Compare measured quality, latency, reported cost, model configuration, and prompt versions."
      />
      <ErrorBox error={result.error} />
      <div className="two-col">
        <Panel
          title="Quality versus latency"
          subtitle="Each point is a persisted evaluation run"
        >
          <div className="chart">
            {latency.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart
                  margin={{ top: 20, left: 0, right: 20, bottom: 15 }}
                >
                  <CartesianGrid stroke="#26303b" strokeDasharray="3 5" />
                  <XAxis
                    type="number"
                    dataKey="latency"
                    name="Latency"
                    unit="ms"
                    stroke="#738092"
                    fontSize={11}
                  />
                  <YAxis
                    type="number"
                    dataKey="quality"
                    name="Success"
                    unit="%"
                    domain={[0, 100]}
                    stroke="#738092"
                    fontSize={11}
                  />
                  <Tooltip
                    contentStyle={chartTheme}
                    cursor={{ strokeDasharray: "3 3" }}
                  />
                  <Scatter data={latency} fill="#91edb8" />
                </ScatterChart>
              </ResponsiveContainer>
            ) : (
              <Empty title="No completed evaluations" />
            )}
          </div>
        </Panel>
        <Panel
          title="Quality versus estimated cost"
          subtitle="Only runs with complete reported usage and configured prices"
        >
          <div className="chart">
            {points.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart>
                  <XAxis
                    type="number"
                    dataKey="cost"
                    name="Cost"
                    unit="$"
                    stroke="#738092"
                  />
                  <YAxis
                    type="number"
                    dataKey="quality"
                    name="Success"
                    unit="%"
                    stroke="#738092"
                  />
                  <Tooltip contentStyle={chartTheme} />
                  <Scatter data={points} fill="#b2a1ec" />
                </ScatterChart>
              </ResponsiveContainer>
            ) : (
              <Empty title="Provider cost is not reported">
                Offline fixture runs do not fabricate token usage or model
                costs.
              </Empty>
            )}
          </div>
        </Panel>
      </div>
      <Panel title="Model and prompt experiments">
        <TableWrap>
          <table>
            <thead>
              <tr>
                <th>Agent version</th>
                <th>Model configuration</th>
                <th>Prompt</th>
                <th>Success</th>
                <th>Mean latency</th>
                <th>Estimated cost</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>
                    <strong>{r.agent}</strong>
                    <small className="cell-sub">{r.version}</small>
                  </td>
                  <td className="mono">
                    {String(r.model.model ?? r.model.provider ?? "unknown")}
                  </td>
                  <td className="mono">v{r.prompt_version}</td>
                  <td>{percent(r.summary.success_rate)}</td>
                  <td>{duration(r.summary.average_latency_ms)}</td>
                  <td>{money(r.summary.average_cost_usd)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      </Panel>
      <Panel title="Judge calibration">
        <div className="padded muted">
          Human-labeled calibration examples are included in the repository. No
          live judge calibration or agreement measurements are claimed for
          offline runs. Missing configured judges return ERROR.
        </div>
      </Panel>
    </>
  );
}
