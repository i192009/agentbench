export interface Page<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
}
export interface Project {
  id: string;
  name: string;
  description: string;
}
export interface Agent {
  id: string;
  name: string;
  description: string;
}
export interface AgentVersion {
  id: string;
  version: string;
  config: Record<string, unknown>;
  checksum: string;
}
export interface Dataset {
  id: string;
  name: string;
  domain: string;
  description: string;
}
export interface DatasetVersion {
  id: string;
  version: number;
  frozen: boolean;
  checksum: string;
  manifest: { split: string };
}
export interface DatasetCase {
  id: string;
  case_id: string;
  body: {
    id: string;
    category: string;
    input: string;
    severity: string;
    tags: string[];
    expected: Record<string, unknown>;
  };
}
export interface Metric {
  name: string;
  score: number | null;
  status: string;
  reason: string;
  evidence: Record<string, unknown>;
}
export interface TraceEvent {
  id: string;
  event: string;
  node: string;
  timestamp: string;
  duration_ms: number;
  data: Record<string, unknown>;
}
export interface Execution {
  output: Record<string, unknown>;
  final_state: string;
  status: string;
  mode: string;
  trace: TraceEvent[];
  tool_calls: {
    name: string;
    arguments: Record<string, unknown>;
    result: unknown;
    status: string;
    duration_ms: number;
  }[];
  documents: {
    id: string;
    version: string;
    content: string;
    facts: Record<string, unknown>;
  }[];
  citations: unknown[];
  latency_ms: number;
  errors: string[];
  safety_violations: string[];
}
export interface CaseResult {
  case_id: string;
  passed: boolean;
  severity: string;
  metrics: Metric[];
  execution: Execution;
}
export interface ResultRow {
  id: string;
  case_id: string;
  passed: boolean;
  body: CaseResult;
}
export interface Gate {
  status: string;
  failures: string[];
  inconclusive: string[];
  policy: Record<string, unknown>;
}
export interface Summary {
  count?: number;
  passed?: number;
  failed?: number;
  success_rate?: number | null;
  safety_violations?: number;
  average_latency_ms?: number | null;
  p95_latency_ms?: number | null;
  average_cost_usd?: number | null;
  metrics?: Record<string, number>;
  gate?: Gate;
  tracking?: { status: string; run_id?: string; reason?: string };
  comparison?: Comparison;
  elapsed_seconds?: number;
  cases_per_second?: number;
}
export interface Run {
  id: string;
  created_at: string;
  status: string;
  total: number;
  completed: number;
  agent: string;
  version: string;
  dataset: string;
  mode: string;
  summary: Summary;
  error?: string;
  snapshot?: {
    agent: {
      name: string;
      version: string;
      model: Record<string, unknown>;
      prompt_version: string;
    };
    dataset: { name: string; cases: unknown[] };
    request: { mode: string };
  };
}
export interface Analytics {
  total_runs: number;
  window: string;
  runs: {
    id: string;
    created_at: string;
    agent: string;
    version: string;
    model: Record<string, unknown>;
    prompt_version: string;
    status: string;
    summary: Summary;
  }[];
}
export interface Comparison {
  status: string;
  paired_count: number;
  effect_size: number;
  delta_ci95: number[];
  new_failures: string[];
  recovered: string[];
  persistent_failures: string[];
  statistical_regression: boolean;
  metric_deltas: Record<string, number>;
  trajectory_changes: {
    case_id: string;
    baseline: string[];
    candidate: string[];
  }[];
  baseline: Summary;
  candidate: Summary;
}
export interface GateRow {
  id: string;
  name: string;
  policy: Record<string, unknown>;
}
