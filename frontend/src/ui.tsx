import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, ArrowUpRight, LoaderCircle, X } from "lucide-react";
import { api } from "./api";

export function useApi<T>(path: string | null, interval?: number) {
  return useQuery<T>({
    queryKey: ["api", path],
    queryFn: () => api<T>(path!),
    enabled: !!path,
    refetchInterval: interval,
  });
}
export function percent(value?: number | null) {
  return value == null ? "—" : (value * 100).toFixed(1) + "%";
}
export function duration(value?: number | null) {
  return value == null
    ? "—"
    : value < 1000
      ? value.toFixed(0) + " ms"
      : (value / 1000).toFixed(2) + " s";
}
export function money(value?: number | null) {
  return value == null ? "Not reported" : "$" + value.toFixed(4);
}
export function human(value: string) {
  return value.replaceAll("_", " ").replaceAll("-", " ");
}
export function Badge({ value }: { value: string }) {
  return (
    <span
      className={
        "badge " +
        (["PASS", "COMPLETED", "completed", "frozen", "ok"].includes(value)
          ? "good"
          : [
                "FAIL",
                "FAILED",
                "ERROR",
                "error",
                "blocked",
                "COMPLETED_WITH_ERRORS",
              ].includes(value)
            ? "bad"
            : ["RUNNING", "QUEUED"].includes(value)
              ? "active"
              : "neutral")
      }
    >
      <span />
      {human(value)}
    </span>
  );
}
export function ErrorBox({ error }: { error: unknown }) {
  return error ? (
    <div className="error" role="alert">
      <AlertCircle size={16} />
      {error instanceof Error ? error.message : String(error)}
    </div>
  ) : null;
}
export function Loading() {
  return (
    <div className="empty">
      <LoaderCircle className="spin" size={22} />
      <p>Loading workspace data…</p>
    </div>
  );
}
export function Empty({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty-icon">∅</div>
      <h3>{title}</h3>
      <p>
        {children ?? "New results will appear here when evaluations finish."}
      </p>
    </div>
  );
}
export function Panel({
  title,
  subtitle,
  action,
  children,
  className = "",
}: {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={"panel " + className}>
      {title && (
        <div className="panel-head">
          <div>
            <h2>{title}</h2>
            {subtitle && <p>{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}
export function Stat({
  label,
  value,
  detail,
  icon,
  tone = "",
}: {
  label: string;
  value: string | number;
  detail?: string;
  icon?: ReactNode;
  tone?: string;
}) {
  return (
    <div className={"stat " + tone}>
      <div className="stat-label">
        {label}
        {icon}
      </div>
      <div className="stat-value">{value}</div>
      {detail && <div className="stat-detail">{detail}</div>}
    </div>
  );
}
export function Modal({
  title,
  children,
  close,
}: {
  title: string;
  children: ReactNode;
  close: () => void;
}) {
  return (
    <div className="modal-backdrop" onClick={close}>
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="panel-head">
          <h2>{title}</h2>
          <button
            className="icon-button"
            onClick={close}
            aria-label="Close dialog"
          >
            <X size={18} />
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}
export function Json({ value }: { value: unknown }) {
  return <pre className="json">{JSON.stringify(value, null, 2)}</pre>;
}
export function TableWrap({ children }: { children: ReactNode }) {
  return <div className="table-scroll">{children}</div>;
}
export function PageIntro({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-intro">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
export function TextLink({
  children,
  onClick,
}: {
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button className="text-link" onClick={onClick}>
      {children}
      <ArrowUpRight size={14} />
    </button>
  );
}
