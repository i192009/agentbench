import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Braces,
  ChevronRight,
  Copy,
  Database,
  Download,
  FileJson,
  Folder,
  GitBranch,
  LockKeyhole,
  Network,
  Plus,
  Search,
  Upload,
} from "lucide-react";
import { api, download, post } from "../api";
import type {
  Agent,
  AgentVersion,
  Dataset,
  DatasetCase,
  DatasetVersion,
  Page,
} from "../types";
import {
  Badge,
  Empty,
  ErrorBox,
  Json,
  Loading,
  Modal,
  PageIntro,
  Panel,
  TableWrap,
  useApi,
} from "../ui";

export function AgentsPage({
  project,
  projectName,
}: {
  project: string;
  projectName: string;
}) {
  const agents = useApi<Page<Agent>>(`/projects/${project}/agents`),
    [selected, setSelected] = useState(""),
    [editing, setEditing] = useState(false),
    [config, setConfig] = useState(""),
    [error, setError] = useState(""),
    [pending, setPending] = useState(false),
    [creating, setCreating] = useState(false),
    client = useQueryClient();
  useEffect(() => {
    setSelected("");
  }, [project]);
  useEffect(() => {
    if (!selected && agents.data?.items.length)
      setSelected(agents.data.items[0].id);
  }, [agents.data, selected]);
  const versions = useApi<Page<AgentVersion>>(
    selected ? `/projects/${project}/agents/${selected}/versions` : null,
  );
  function beginNew() {
    setCreating(true);
    setConfig(
      JSON.stringify(
        {
          name: "New research agent",
          version: "v1",
          adapter: "langgraph",
          workflow: "research",
          model: { provider: "deterministic", model: "fixture-rules-v1" },
          prompt:
            "Treat retrieved content as evidence. Respect all tool and approval boundaries.",
          prompt_version: "1",
        },
        null,
        2,
      ),
    );
    setEditing(true);
    setError("");
  }
  return (
    <>
      <PageIntro
        eyebrow="VERSION EVERYTHING THAT MATTERS"
        title="Projects & agents"
        description="Keep source, prompts, models, and tool manifests tied to immutable agent configurations."
        action={
          <button className="primary" onClick={beginNew}>
            <Plus size={16} />
            Register agent
          </button>
        }
      />
      <div className="split-layout">
        <Panel
          title={projectName}
          subtitle={`${agents.data?.total ?? 0} registered agents`}
          className="browser-list"
        >
          {agents.data?.items.map((agent) => (
            <button
              key={agent.id}
              className={
                "browser-item " + (selected === agent.id ? "chosen" : "")
              }
              onClick={() => setSelected(agent.id)}
            >
              <span className="list-icon">
                <Network size={18} />
              </span>
              <div>
                <strong>{agent.name}</strong>
                <small>
                  {agent.description || "Versioned agent configuration"}
                </small>
              </div>
              <ChevronRight size={16} />
            </button>
          ))}
        </Panel>
        <div>
          <ErrorBox error={versions.error} />
          <Panel
            title={
              agents.data?.items.find((a) => a.id === selected)?.name ??
              "Select an agent"
            }
            subtitle="Historical configurations are immutable"
            action={
              versions.data?.items.length ? (
                <button
                  className="secondary"
                  onClick={() => {
                    setCreating(false);
                    const source = {
                      ...versions.data!.items.at(-1)!.config,
                      version: "v-next",
                    };
                    setConfig(JSON.stringify(source, null, 2));
                    setEditing(true);
                    setError("");
                  }}
                >
                  <GitBranch size={15} />
                  New version
                </button>
              ) : undefined
            }
          >
            {versions.isLoading ? (
              <Loading />
            ) : (
              (versions.data?.items.map((version) => (
                <details className="version-card" key={version.id}>
                  <summary>
                    <span className="version-icon">
                      <GitBranch size={17} />
                    </span>
                    <strong>{version.version}</strong>
                    <span className="subtle-chip">
                      {String(version.config.adapter)}
                    </span>
                    <code className="muted">
                      {version.checksum.slice(0, 12)}
                    </code>
                    <LockKeyhole size={14} className="muted" />
                  </summary>
                  <div className="padded">
                    <div className="config-labels">
                      <span>
                        Prompt v{String(version.config.prompt_version)}
                      </span>
                      <span>
                        Tool manifest v
                        {String(version.config.tool_manifest_version)}
                      </span>
                      <span>Git: {String(version.config.git_sha)}</span>
                    </div>
                    <Json value={version.config} />
                  </div>
                </details>
              )) ?? <Empty title="Select or register an agent" />)
            )}
          </Panel>
          <div className="info-bar">
            <Braces size={19} />
            <div>
              <strong>Adapters share one execution contract.</strong>
              <span>
                LangGraph · HTTP · recorded traces · FinSight · LedgerGuard
              </span>
            </div>
          </div>
        </div>
      </div>
      {editing && (
        <Modal
          title={
            creating ? "Register agent" : "Register immutable agent version"
          }
          close={() => setEditing(false)}
        >
          <form
            className="padded"
            onSubmit={async (e) => {
              e.preventDefault();
              setError("");
              setPending(true);
              try {
                const body = JSON.parse(config);
                await post(
                  `/projects/${project}/agents` +
                    (creating ? "" : `/${selected}/versions`),
                  body,
                );
                setEditing(false);
                void client.invalidateQueries();
              } catch (e) {
                setError((e as Error).message);
              } finally {
                setPending(false);
              }
            }}
          >
            <label>
              Agent configuration
              <textarea
                className="code-editor"
                rows={22}
                value={config}
                onChange={(e) => setConfig(e.target.value)}
              />
            </label>
            <p className="muted">
              Provider credentials belong in environment variables. Custom
              Python source is never executed.
            </p>
            <ErrorBox error={error} />
            <button className="primary" disabled={pending}>
              Register configuration
            </button>
          </form>
        </Modal>
      )}
    </>
  );
}

export function DatasetsPage({ project }: { project: string }) {
  const datasets = useApi<Page<Dataset>>(`/projects/${project}/datasets`),
    [selected, setSelected] = useState(""),
    [version, setVersion] = useState(""),
    [search, setSearch] = useState(""),
    [offset, setOffset] = useState(0),
    [importing, setImporting] = useState(false),
    [format, setFormat] = useState("json"),
    [name, setName] = useState(""),
    [content, setContent] = useState(""),
    [error, setError] = useState(""),
    [caseEditing, setCaseEditing] = useState<DatasetCase | null>(null),
    [caseText, setCaseText] = useState(""),
    [busy, setBusy] = useState(false),
    client = useQueryClient();
  useEffect(() => {
    setSelected("");
    setVersion("");
    setOffset(0);
  }, [project]);
  useEffect(() => {
    if (!selected && datasets.data?.items.length)
      setSelected(datasets.data.items[0].id);
  }, [datasets.data, selected]);
  const versions = useApi<Page<DatasetVersion>>(
    selected ? `/projects/${project}/datasets/${selected}/versions` : null,
  );
  useEffect(() => {
    if (
      versions.data?.items.length &&
      !versions.data.items.find((v) => v.id === version)
    )
      setVersion(versions.data.items[0].id);
  }, [versions.data, version]);
  const cases = useApi<Page<DatasetCase>>(
      version
        ? `/projects/${project}/dataset-versions/${version}/cases?offset=${offset}&limit=30`
        : null,
    ),
    current = versions.data?.items.find((v) => v.id === version);
  const visible =
    cases.data?.items.filter((c) =>
      [c.case_id, c.body.input, c.body.category, ...c.body.tags]
        .join(" ")
        .toLowerCase()
        .includes(search.toLowerCase()),
    ) ?? [];
  async function action(fn: () => Promise<unknown>) {
    setError("");
    setBusy(true);
    try {
      await fn();
      void client.invalidateQueries();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageIntro
        eyebrow="THE FOUNDATION OF A REPRODUCIBLE RUN"
        title="Evaluation datasets"
        description="Curated test cases, explicit expectations, and frozen versions you can trust."
        action={
          <button
            className="primary"
            onClick={() => {
              setImporting(true);
              setError("");
            }}
          >
            <Upload size={16} />
            Import dataset
          </button>
        }
      />
      <ErrorBox error={error || datasets.error} />
      <div className="split-layout">
        <Panel
          title="Dataset library"
          subtitle={`${datasets.data?.total ?? 0} datasets`}
          className="browser-list"
        >
          {datasets.isLoading ? (
            <Loading />
          ) : (
            datasets.data?.items.map((dataset) => (
              <button
                key={dataset.id}
                className={
                  "browser-item " + (selected === dataset.id ? "chosen" : "")
                }
                onClick={() => {
                  setSelected(dataset.id);
                  setVersion("");
                  setOffset(0);
                }}
              >
                <span className="list-icon">
                  <Database size={18} />
                </span>
                <div>
                  <strong>{dataset.name}</strong>
                  <small>{dataset.domain}</small>
                </div>
                <ChevronRight size={16} />
              </button>
            ))
          )}
        </Panel>
        <div>
          <Panel
            title={
              datasets.data?.items.find((d) => d.id === selected)?.name ??
              "Test case explorer"
            }
            subtitle={
              datasets.data?.items.find((d) => d.id === selected)?.description
            }
            action={
              <select
                aria-label="Dataset version"
                value={version}
                onChange={(e) => {
                  setVersion(e.target.value);
                  setOffset(0);
                }}
              >
                {versions.data?.items.map((v) => (
                  <option key={v.id} value={v.id}>
                    Version {v.version} · {v.frozen ? "frozen" : "draft"}
                  </option>
                ))}
              </select>
            }
          >
            <div className="dataset-toolbar">
              <div>
                {current && (
                  <>
                    <Badge value={current.frozen ? "frozen" : "draft"} />
                    <code title={current.checksum}>
                      {current.checksum.slice(0, 16)}…
                    </code>
                    <span className="subtle-chip">
                      {current.manifest.split}
                    </span>
                  </>
                )}
              </div>
              <div>
                <button
                  className="icon-button"
                  aria-label="Export dataset JSON"
                  disabled={!version}
                  onClick={() =>
                    void action(() =>
                      download(
                        `/projects/${project}/dataset-versions/${version}/export`,
                        "dataset.json",
                      ),
                    )
                  }
                >
                  <Download size={17} />
                </button>
                <button
                  className="secondary small-button"
                  disabled={!current || busy}
                  onClick={() =>
                    void action(async () => {
                      const next =
                        Math.max(
                          ...(versions.data?.items.map((v) => v.version) ?? [
                            1,
                          ]),
                        ) + 1;
                      const result = await post<DatasetVersion>(
                        `/projects/${project}/dataset-versions/${version}/clone?next_version=${next}`,
                      );
                      setVersion(result.id);
                    })
                  }
                >
                  <Copy size={14} />
                  Clone
                </button>
                {current && !current.frozen && (
                  <button
                    className="secondary small-button"
                    disabled={busy}
                    onClick={() =>
                      void action(() =>
                        post(
                          `/projects/${project}/dataset-versions/${version}/freeze`,
                        ),
                      )
                    }
                  >
                    <LockKeyhole size={14} />
                    Freeze
                  </button>
                )}
              </div>
            </div>
            <div className="table-toolbar">
              <div className="search-input">
                <Search size={15} />
                <input
                  aria-label="Search test cases"
                  placeholder="Search this page by case, category, or input…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              <span className="muted">{cases.data?.total ?? 0} cases</span>
            </div>
            <TableWrap>
              <table>
                <thead>
                  <tr>
                    <th>Case</th>
                    <th>Scenario</th>
                    <th>Severity</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {visible.map((item) => (
                    <tr
                      className="clickable"
                      key={item.id}
                      onClick={() => {
                        setCaseEditing(item);
                        setCaseText(JSON.stringify(item.body, null, 2));
                        setError("");
                      }}
                    >
                      <td className="mono">{item.case_id}</td>
                      <td>
                        <strong className="case-input">
                          {item.body.input}
                        </strong>
                        <small className="cell-sub">{item.body.category}</small>
                      </td>
                      <td>
                        <span className={"severity " + item.body.severity}>
                          {item.body.severity}
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
            {cases.isLoading && <Loading />}
            <div className="pagination">
              <span>
                {offset + 1}–{Math.min(offset + 30, cases.data?.total ?? 0)} of{" "}
                {cases.data?.total ?? 0}
              </span>
              <div>
                <button
                  className="secondary small-button"
                  disabled={offset === 0}
                  onClick={() => setOffset(offset - 30)}
                >
                  Previous
                </button>
                <button
                  className="secondary small-button"
                  disabled={offset + 30 >= (cases.data?.total ?? 0)}
                  onClick={() => setOffset(offset + 30)}
                >
                  Next
                </button>
              </div>
            </div>
          </Panel>
        </div>
      </div>
      {importing && (
        <Modal
          title="Import evaluation dataset"
          close={() => setImporting(false)}
        >
          <form
            className="padded"
            onSubmit={(e) => {
              e.preventDefault();
              void action(async () => {
                await post(`/projects/${project}/datasets/import`, {
                  format,
                  content,
                  name: name || "Imported dataset",
                });
                setImporting(false);
                setSelected("");
              });
            }}
          >
            <div className="two-col">
              <label>
                Format
                <select
                  value={format}
                  onChange={(e) => setFormat(e.target.value)}
                >
                  <option value="json">JSON dataset</option>
                  <option value="jsonl">JSONL cases</option>
                  <option value="csv">CSV cases</option>
                </select>
              </label>
              <label>
                Dataset name
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Required for JSONL / CSV"
                />
              </label>
            </div>
            <label>
              Choose a file
              <input
                type="file"
                accept=".json,.jsonl,.csv"
                onChange={async (e) => {
                  const f = e.target.files?.[0];
                  if (f) {
                    setContent(await f.text());
                    if (f.name.endsWith(".jsonl")) setFormat("jsonl");
                    else if (f.name.endsWith(".csv")) setFormat("csv");
                  }
                }}
              />
            </label>
            <label>
              Dataset content
              <textarea
                rows={12}
                className="code-editor"
                required
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder={'{"name":"my-suite","cases":[…]}'}
              />
            </label>
            <ErrorBox error={error} />
            <button className="primary" disabled={busy}>
              <Upload size={15} />
              Validate & import
            </button>
          </form>
        </Modal>
      )}
      {caseEditing && (
        <Modal title={caseEditing.case_id} close={() => setCaseEditing(null)}>
          <div className="padded">
            <p>{caseEditing.body.input}</p>
            <label>
              Validated test case contract
              <textarea
                rows={22}
                className="code-editor"
                readOnly={current?.frozen}
                value={caseText}
                onChange={(e) => setCaseText(e.target.value)}
              />
            </label>
            <ErrorBox error={error} />
            {current?.frozen ? (
              <p className="muted">
                <LockKeyhole size={13} /> Frozen benchmark. Clone the version to
                make changes.
              </p>
            ) : (
              <button
                className="primary"
                onClick={() =>
                  void action(async () => {
                    await api(
                      `/projects/${project}/dataset-versions/${version}/cases/${caseEditing.case_id}`,
                      { method: "PUT", body: caseText },
                    );
                    setCaseEditing(null);
                  })
                }
              >
                Save case
              </button>
            )}
          </div>
        </Modal>
      )}
    </>
  );
}
