import { afterEach, describe, expect, it, vi } from "vitest";
import { api, refreshSession, setToken } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
  setToken("");
});
describe("authenticated API", () => {
  it("refreshes once and retries with the rotated access token", async () => {
    setToken("expired");
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(new Response("{}", { status: 401 }))
      .mockResolvedValueOnce(
        new Response('{"access_token":"rotated"}', { status: 200 }),
      )
      .mockResolvedValueOnce(new Response('{"items":[]}', { status: 200 }));
    vi.stubGlobal("fetch", fetcher);
    expect(await api("/projects")).toEqual({ items: [] });
    expect(fetcher.mock.calls[2][1].headers.Authorization).toBe(
      "Bearer rotated",
    );
  });
  it("preserves server validation errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response('{"detail":"Frozen version is immutable"}', {
            status: 409,
          }),
        ),
    );
    await expect(api("/dataset")).rejects.toThrow(
      "Frozen version is immutable",
    );
  });
  it("does not claim authentication when refresh fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("{}", { status: 401 })),
    );
    expect(await refreshSession()).toBe(false);
  });
});
