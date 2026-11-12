import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowUpRight,
  Beaker,
  Bell,
  BookOpen,
  ChevronDown,
  CircleHelp,
  Database,
  Fingerprint,
  FlaskConical,
  GitCompareArrows,
  LayoutDashboard,
  LogOut,
  Menu,
  Network,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  Terminal,
  Workflow,
} from "lucide-react";
import { api, post, refreshSession, setToken } from "./api";
import type { Page, Project } from "./types";
import { ErrorBox, useApi } from "./ui";
import {
  Overview,
  AnalyticsPage,
  GatesPage,
  ComparisonPage,
  AdversarialPage,
} from "./pages/insights";
import { AgentsPage, DatasetsPage } from "./pages/registry";
import { LaunchPage, ResultsPage, TracesPage } from "./pages/runs";

const navigation = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "agents", label: "Projects & agents", icon: Network },
  { id: "datasets", label: "Datasets", icon: Database },
  { id: "launch", label: "Run evaluation", icon: FlaskConical },
  { id: "results", label: "Evaluation results", icon: Activity },
  { id: "traces", label: "Trace explorer", icon: Workflow },
  { id: "comparison", label: "Regression comparison", icon: GitCompareArrows },
  { id: "adversarial", label: "Adversarial testing", icon: Fingerprint },
  { id: "gates", label: "Quality gates", icon: ShieldCheck },
  { id: "analytics", label: "Experiment analytics", icon: Sparkles },
];
function readRoute() {
  const [page, run] = location.hash.slice(1).split("/");
  return { page: page || "overview", run: run || "" };
}

function Login({ onSuccess }: { onSuccess: () => void }) {
  const [email, setEmail] = useState("demo@agentbench.local"),
    [password, setPassword] = useState(""),
    [error, setError] = useState(""),
    [pending, setPending] = useState(false),
    [register, setRegister] = useState(false);
  return (
    <main className="login">
      <div className="login-art">
        <div className="brand">
          <span className="brand-mark">A</span>agentbench
          <span className="beta">BETA</span>
        </div>
        <div className="login-message">
          <div className="eyebrow">CONFIDENCE, MEASURED.</div>
          <h1>
            Know what your
            <br />
            agents actually do.
          </h1>
          <p>
            Test the workflow. Follow the evidence.
            <br />
            Catch regressions before they reach production.
          </p>
          <div className="terminal-art">
            <div>
              <span />
              agentbench eval run
            </div>
            <p>→ Execute agent workflow</p>
            <p>→ Capture MCP tool trajectory</p>
            <p>→ Validate evidence & authorization</p>
            <p className="mint">→ Apply deployment quality gate</p>
          </div>
        </div>
        <small>
          Built for the space between “it works” and “we can prove it.”
        </small>
      </div>
      <div className="login-form">
        <div>
          <div className="eyebrow">YOUR EVALUATION WORKSPACE</div>
          <h2>{register ? "Create your workspace" : "Welcome back"}</h2>
          <p>
            {register
              ? "Start an isolated organization for your evaluations."
              : "Sign in to your agent reliability lab."}
          </p>
          <form
            onSubmit={async (event) => {
              event.preventDefault();
              setError("");
              setPending(true);
              try {
                const data = await post<{ access_token: string }>(
                  "/auth/" + (register ? "register" : "login"),
                  { email, password },
                );
                setToken(data.access_token);
                onSuccess();
              } catch (e) {
                setError((e as Error).message);
              } finally {
                setPending(false);
              }
            }}
          >
            <label>
              Email address
              <input
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
            <label>
              Password
              <input
                type="password"
                autoComplete={register ? "new-password" : "current-password"}
                minLength={12}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            <ErrorBox error={error} />
            <button className="primary" disabled={pending}>
              {pending
                ? "Connecting…"
                : register
                  ? "Create workspace"
                  : "Sign in"}
              <ArrowUpRight size={17} />
            </button>
          </form>
          <button
            className="text-link login-switch"
            onClick={() => setRegister(!register)}
          >
            {register
              ? "Already have an account? Sign in"
              : "Create a separate workspace"}
          </button>
          <p className="login-note">
            <ShieldCheck size={15} />
            Secure refresh sessions · project-level access
          </p>
        </div>
      </div>
    </main>
  );
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(false),
    [checking, setChecking] = useState(true),
    [route, setRoute] = useState(readRoute),
    [project, setProject] = useState(""),
    [mobile, setMobile] = useState(false);
  const client = useQueryClient();
  useEffect(() => {
    void refreshSession().then((ok) => {
      setAuthenticated(ok);
      setChecking(false);
    });
  }, []);
  useEffect(() => {
    const update = () => setRoute(readRoute());
    addEventListener("hashchange", update);
    return () => removeEventListener("hashchange", update);
  }, []);
  const projects = useApi<Page<Project>>(authenticated ? "/projects" : null);
  useEffect(() => {
    if (!project && projects.data?.items.length)
      setProject(projects.data.items[0].id);
  }, [project, projects.data]);
  const go = (page: string, run = "") => {
    location.hash = page + (run ? "/" + run : "");
    setMobile(false);
  };
  if (checking)
    return (
      <div className="boot">
        <span className="brand-mark">A</span>
        <span>Connecting to AgentBench…</span>
      </div>
    );
  if (!authenticated)
    return (
      <Login
        onSuccess={() => {
          setAuthenticated(true);
          void client.invalidateQueries();
        }}
      />
    );
  const current = projects.data?.items.find((p) => p.id === project);
  return (
    <div className="app">
      <aside className={mobile ? "sidebar open" : "sidebar"}>
        <a className="brand" href="#overview">
          <span className="brand-mark">A</span>agentbench
          <span className="brand-dot" />
        </a>
        <div className="workspace">
          <span className="workspace-avatar">AL</span>
          <div>
            <strong>Agent Reliability Lab</strong>
            <small>Development workspace</small>
          </div>
          <ChevronDown size={14} />
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav aria-label="Main navigation">
          {navigation.map((item, i) => (
            <div key={item.id}>
              {i === 3 && (
                <div className="nav-label secondary-label">EVALUATION</div>
              )}
              {i === 8 && (
                <div className="nav-label secondary-label">OPERATIONS</div>
              )}
              <button
                className={
                  route.page === item.id ? "nav-item selected" : "nav-item"
                }
                onClick={() => go(item.id)}
              >
                <item.icon size={17} />
                <span>{item.label}</span>
                {item.id === "launch" && (
                  <Plus size={13} className="nav-plus" />
                )}
              </button>
            </div>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sandbox-note">
            <div>
              <span className="live-dot" />
              Synthetic sandbox
            </div>
            <p>
              No live financial operations.
              <br />
              No model keys needed offline.
            </p>
          </div>
          <a href="http://localhost:8010/docs" target="_blank" rel="noreferrer">
            <BookOpen size={16} />
            API documentation
            <ArrowUpRight size={13} />
          </a>
          <button
            onClick={async () => {
              await post("/auth/logout");
              setToken("");
              client.clear();
              setAuthenticated(false);
            }}
          >
            <LogOut size={16} />
            Sign out
          </button>
          <div className="sidebar-user">
            <span className="user-avatar">D</span>
            <div>
              <strong>Evaluation workspace</strong>
              <small>AgentBench v0.1.0</small>
            </div>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div>
            <button
              className="icon-button mobile-menu"
              aria-label="Open navigation"
              onClick={() => setMobile(!mobile)}
            >
              <Menu size={20} />
            </button>
            <span className="breadcrumb">
              Workspace <span>/</span>{" "}
              <strong>
                {navigation.find((n) => n.id === route.page)?.label ||
                  "Overview"}
              </strong>
            </span>
          </div>
          <div className="topbar-actions">
            <a
              href="http://localhost:5050"
              target="_blank"
              rel="noreferrer"
              className="mlflow-link"
            >
              <span className="live-dot" />
              MLflow
              <ArrowUpRight size={12} />
            </a>
            <span className="environment-tag">LOCAL</span>
            <a
              className="icon-button"
              href="http://localhost:8010/docs"
              aria-label="Help and API reference"
              target="_blank"
              rel="noreferrer"
            >
              <CircleHelp size={17} />
            </a>
            <span className="user-avatar small">D</span>
          </div>
        </header>
        <main className="content">
          <div className="project-bar">
            <label>
              <span className="project-square">
                <Beaker size={13} />
              </span>
              <select
                aria-label="Project"
                value={project}
                onChange={(e) => {
                  setProject(e.target.value);
                  go("overview");
                }}
              >
                {projects.data?.items.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>
            <span>
              <span className="live-dot" />
              Connected to evaluation API
            </span>
          </div>
          <ErrorBox error={projects.error} />
          {!project ? (
            <div className="empty">
              <h2>Create your first project</h2>
              <p>
                Your project keeps agents, datasets, and evaluation history
                together.
              </p>
              <button
                className="primary"
                onClick={async () => {
                  const name = prompt("Project name");
                  if (name) {
                    const p = await post<Project>("/projects", { name });
                    setProject(p.id);
                    void client.invalidateQueries();
                  }
                }}
              >
                Create project
                <Plus size={16} />
              </button>
            </div>
          ) : (
            <>
              {route.page === "overview" && (
                <Overview project={project} go={go} />
              )}
              {route.page === "agents" && (
                <AgentsPage
                  project={project}
                  projectName={current?.name ?? ""}
                />
              )}
              {route.page === "datasets" && <DatasetsPage project={project} />}
              {route.page === "launch" && (
                <LaunchPage project={project} go={go} />
              )}
              {route.page === "results" && (
                <ResultsPage project={project} runId={route.run} go={go} />
              )}
              {route.page === "traces" && (
                <TracesPage project={project} runId={route.run} />
              )}
              {route.page === "comparison" && (
                <ComparisonPage project={project} />
              )}
              {route.page === "adversarial" && (
                <AdversarialPage project={project} go={go} />
              )}
              {route.page === "gates" && <GatesPage project={project} />}
              {route.page === "analytics" && (
                <AnalyticsPage project={project} />
              )}
            </>
          )}
          <footer className="footer">
            <span>
              <span className="brand-dot" />
              AgentBench <span className="muted">/</span> Evidence before
              confidence.
            </span>
            <span>
              Offline fixtures ≠ live model reasoning{" "}
              <span className="muted">·</span> v0.1.0
            </span>
          </footer>
        </main>
      </div>
    </div>
  );
}
