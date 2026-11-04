import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, getProjectStatus } from "./client";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

describe("apiRequest", () => {
  beforeEach(() => fetchMock.mockReset());

  it("explains how to recover when the local API is unreachable", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    const failure = getProjectStatus("project-1");

    await expect(failure).rejects.toBeInstanceOf(ApiError);
    await expect(getProjectStatusError()).resolves.toMatchObject({ status: 0 });
    await expect(failure).rejects.toThrow(
      "SelectIQ cannot reach its local API at http://localhost:8000. Start it with scripts/dev.sh and try again.",
    );
  });

  it("uses the API's detail message for HTTP errors", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: "Project project-1 was not found." }),
    } as Response);

    await expect(getProjectStatus("project-1")).rejects.toThrow("Project project-1 was not found.");
  });
});

async function getProjectStatusError(): Promise<unknown> {
  fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));
  return getProjectStatus("project-1").catch((error: unknown) => error);
}
