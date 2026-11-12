let accessToken = "";
export function setToken(token: string) {
  accessToken = token;
}
export function token() {
  return accessToken;
}

let refreshing: Promise<boolean> | null = null;
export async function refreshSession(): Promise<boolean> {
  if (!refreshing)
    refreshing = fetch("/api/auth/refresh", {
      method: "POST",
      credentials: "include",
    })
      .then(async (response) => {
        if (!response.ok) return false;
        const data = (await response.json()) as { access_token: string };
        setToken(data.access_token);
        return true;
      })
      .catch(() => false)
      .finally(() => {
        refreshing = null;
      });
  return refreshing;
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
  retried = false,
): Promise<T> {
  const response = await fetch("/api" + path, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: "Bearer " + accessToken } : {}),
      ...options.headers,
    },
  });
  if (
    response.status === 401 &&
    !retried &&
    !path.startsWith("/auth/") &&
    (await refreshSession())
  )
    return api<T>(path, options, true);
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as {
      detail?: unknown;
    };
    throw new Error(
      typeof payload.detail === "string"
        ? payload.detail
        : JSON.stringify(payload.detail ?? `HTTP ${response.status}`),
    );
  }
  return response.json() as Promise<T>;
}
export function post<T>(path: string, body?: unknown) {
  return api<T>(path, {
    method: "POST",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}
export async function download(path: string, filename: string) {
  const response = await fetch("/api" + path, {
    credentials: "include",
    headers: { Authorization: "Bearer " + accessToken },
  });
  if (!response.ok) throw new Error("Export failed");
  const url = URL.createObjectURL(await response.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
export async function followRun(
  path: string,
  signal: AbortSignal,
  onEvent: (name: string) => void,
) {
  let cursor = "";
  while (!signal.aborted) {
    try {
      const response = await fetch(
        "/api" + path + (cursor ? "?after=" + encodeURIComponent(cursor) : ""),
        { signal, headers: { Authorization: "Bearer " + accessToken } },
      );
      if (response.status === 401 && (await refreshSession())) continue;
      if (!response.ok || !response.body) return;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (!signal.aborted) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() ?? "";
        for (const chunk of chunks) {
          const id = chunk.match(/^id: (.+)$/m)?.[1];
          const name = chunk.match(/^event: (.+)$/m)?.[1];
          if (id) cursor = id;
          if (name) {
            onEvent(name);
            if (["RunCompleted", "RunCancelled"].includes(name)) return;
          }
        }
      }
    } catch (error) {
      if (signal.aborted) return;
    }
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
}
