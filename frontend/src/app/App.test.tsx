import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

describe("gallery import", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    window.localStorage.clear();
  });

  it("selects files and displays partial upload results", async () => {
    fetchMock
      .mockResolvedValueOnce(response({ projectId: "project-1", acceptedCount: 0 }, 201))
      .mockResolvedValueOnce(
        response({
          accepted: [{ photoId: "photo-1", originalFilename: "valid.jpg", width: 10, height: 10, byteSize: 10, state: "pending" }],
          rejected: [{ filename: "broken.jpg", code: "invalid_jpeg", message: "The JPEG could not be decoded." }],
          batchAcceptedCount: 1,
          batchRejectedCount: 1,
          acceptedCount: 1,
        }),
      );

    render(<App />);
    const input = screen.getByLabelText("Choose files");
    const files = [
      new File(["valid"], "valid.jpg", { type: "image/jpeg" }),
      new File(["broken"], "broken.jpg", { type: "image/jpeg" }),
    ];
    fireEvent.change(input, { target: { files } });
    expect(screen.getByText("2 files selected")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Import selected photographs" }));

    await waitFor(() => expect(screen.getByLabelText("1 photos accepted")).toBeInTheDocument());
    expect(screen.getByText("1 accepted, 1 rejected in this upload.")).toBeInTheDocument();
    expect(screen.getByText("broken.jpg")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Analyze gallery" })).toBeInTheDocument();
  });

  it("restores an existing project's accepted count", async () => {
    window.localStorage.setItem("selectiq.projectId", "project-1");
    fetchMock.mockResolvedValueOnce(
      response({
        projectId: "project-1",
        acceptedCount: 14,
        remainingCapacity: 16,
        failures: [],
        prompt: "Prioritize candid emotion.",
        target: 5,
        analysisStatus: "completed",
        analysisTotal: 14,
        analysisCompleted: 14,
        analysisFailed: 0,
        analysisFailures: [],
        analysisModel: "ViT-B-32",
      }),
    );

    render(<App />);

    await waitFor(() => expect(screen.getByLabelText("14 photos accepted")).toBeInTheDocument());
    expect(screen.getByText("16 spaces remaining")).toBeInTheDocument();
    expect(screen.getByText(/ViT-B-32 completed the analysis/i)).toBeInTheDocument();
  });

  it("surfaces analysis failures and starts a retry", async () => {
    window.localStorage.setItem("selectiq.projectId", "project-1");
    fetchMock
      .mockResolvedValueOnce(
        response({
          projectId: "project-1",
          acceptedCount: 2,
          remainingCapacity: 28,
          failures: [],
          prompt: "Prioritize candid emotion.",
          target: 1,
          analysisStatus: "partial_failure",
          analysisTotal: 2,
          analysisCompleted: 1,
          analysisFailed: 1,
          analysisFailures: [{ photoId: "photo-2", originalFilename: "broken.jpg", code: "inference_failed", message: "Inference failed." }],
        }),
      )
      .mockResolvedValueOnce(response({ projectId: "project-1", analysisStatus: "queued" }, 202));

    render(<App />);

    const retry = await screen.findByRole("button", { name: "Retry analysis" });
    expect(screen.getByText("broken.jpg")).toBeInTheDocument();
    fireEvent.click(retry);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(fetchMock.mock.calls[1][0]).toContain("/projects/project-1/analyze");
  });
});

describe("prompt and target", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    window.localStorage.clear();
  });

  it("saves a nonblank creative brief and valid target", async () => {
    fetchMock
      .mockResolvedValueOnce(response({ projectId: "project-1", acceptedCount: 0 }, 201))
      .mockResolvedValueOnce(
        response({
          accepted: Array.from({ length: 15 }, (_, index) => ({
            photoId: `photo-${index}`,
            originalFilename: `photo-${index}.jpg`,
            width: 10,
            height: 10,
            byteSize: 10,
            state: "pending",
          })),
          rejected: [],
          batchAcceptedCount: 15,
          batchRejectedCount: 0,
          acceptedCount: 15,
        }),
      )
      .mockResolvedValueOnce(
        response({
          projectId: "project-1",
          prompt: "Prioritize candid emotion and energetic action.",
          target: 5,
          acceptedCount: 15,
        }),
      );
    render(<App />);
    const files = Array.from(
      { length: 15 },
      (_, index) => new File(["jpeg"], `photo-${index}.jpg`, { type: "image/jpeg" }),
    );
    fireEvent.change(screen.getByLabelText("Choose files"), { target: { files } });
    fireEvent.click(screen.getByRole("button", { name: "Import selected photographs" }));
    await waitFor(() => expect(screen.getByLabelText("15 photos accepted")).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText("Creative brief"), {
      target: { value: "Prioritize candid emotion and energetic action." },
    });
    fireEvent.change(screen.getByLabelText("Target number of photographs"), {
      target: { value: "5" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save brief and target" }));

    await waitFor(() => expect(screen.getByText(/brief and target saved/i)).toBeInTheDocument());
    expect(fetchMock).toHaveBeenLastCalledWith(
      "http://localhost:8000/projects/project-1/brief",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: "Prioritize candid emotion and energetic action.",
          target: 5,
        }),
      }),
    );
  });

  it("restores the saved creative brief and target from the project session", async () => {
    window.localStorage.setItem("selectiq.projectId", "project-1");
    fetchMock.mockResolvedValueOnce(
      response({
        projectId: "project-1",
        acceptedCount: 18,
        remainingCapacity: 12,
        failures: [],
        prompt: "Preserve relationships and quiet reactions.",
        target: 5,
      }),
    );

    render(<App />);

    expect(await screen.findByLabelText("Creative brief")).toHaveValue(
      "Preserve relationships and quiet reactions.",
    );
    expect(screen.getByLabelText("Target number of photographs")).toHaveValue(5);
  });

  it("does not submit a blank prompt", async () => {
    window.localStorage.setItem("selectiq.projectId", "project-1");
    fetchMock.mockResolvedValueOnce(
      response({
        projectId: "project-1",
        acceptedCount: 4,
        remainingCapacity: 26,
        failures: [],
        prompt: null,
        target: null,
      }),
    );
    render(<App />);
    await screen.findByLabelText("Creative brief");
    fireEvent.change(screen.getByLabelText("Creative brief"), { target: { value: "   " } });
    fireEvent.change(screen.getByLabelText("Target number of photographs"), {
      target: { value: "2" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save brief and target" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/brief.*blank|enter.*brief/i);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("does not submit a target larger than the accepted count", async () => {
    window.localStorage.setItem("selectiq.projectId", "project-1");
    fetchMock.mockResolvedValueOnce(
      response({
        projectId: "project-1",
        acceptedCount: 4,
        remainingCapacity: 26,
        failures: [],
        prompt: null,
        target: null,
      }),
    );
    render(<App />);
    await screen.findByLabelText("Creative brief");
    fireEvent.change(screen.getByLabelText("Creative brief"), {
      target: { value: "Keep the strongest moments." },
    });
    fireEvent.change(screen.getByLabelText("Target number of photographs"), {
      target: { value: "5" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save brief and target" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/target.*4|accepted.*4/i);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("brief interpretation", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    window.localStorage.clear();
    window.localStorage.setItem("selectiq.projectId", "project-1");
  });

  const completedStatus = {
    projectId: "project-1",
    acceptedCount: 3,
    remainingCapacity: 27,
    failures: [],
    prompt: "Best lit, nicest smiles.",
    target: 2,
    analysisStatus: "completed",
    analysisTotal: 3,
    analysisCompleted: 3,
    analysisFailed: 0,
    analysisFailures: [],
    analysisModel: "ViT-B-32",
  };

  function route(interpretation: unknown, posted?: unknown, nextComparison?: unknown) {
    fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/status")) return response(completedStatus);
      if (url.endsWith("/interpretation") && init?.method === "POST") {
        return response(posted ?? { projectId: "project-1", status: "queued" }, 202);
      }
      if (url.endsWith("/interpretation")) return response(interpretation);
      if (url.endsWith("/comparisons/next") && nextComparison) {
        return response(nextComparison);
      }
      if (url.endsWith("/recommendations")) {
        return response({ detail: "Project project-1 has no proposal yet." }, 404);
      }
      throw new Error(`Unexpected request ${url}`);
    });
  }

  const notStarted = {
    projectId: "project-1",
    status: "not_started",
    provider: null,
    model: null,
    summary: null,
    positiveDescriptors: [],
    negativeDescriptors: [],
    photoNotes: [],
    errorCode: null,
    errorMessage: null,
    rankingBasis: "brief_relevance",
    ranking: [],
  };

  it("offers proposal generation with the saved target once analysis completes", async () => {
    route(notStarted);
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Generate a proposal" })).toBeInTheDocument();
    expect(screen.getByText("Target: 2 photographs, from your saved brief.")).toBeInTheDocument();
  });

  it("opens the first comparison from the completed analysis workflow", async () => {
    route(
      {
        projectId: "project-1",
        status: "not_started",
        provider: null,
        model: null,
        summary: null,
        positiveDescriptors: [],
        negativeDescriptors: [],
        photoNotes: [],
        errorCode: null,
        errorMessage: null,
        rankingBasis: "brief_relevance",
        ranking: [],
      },
      undefined,
      {
        projectId: "project-1",
        sequence: 1,
        budget: 5,
        completed: false,
        photoA: {
          photoId: "photo-a",
          originalFilename: "candid.jpg",
          imageUrl: "/projects/project-1/photos/photo-a/content",
        },
        photoB: {
          photoId: "photo-b",
          originalFilename: "portrait.jpg",
          imageUrl: "/projects/project-1/photos/photo-b/content",
        },
      },
    );
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "Start comparisons" }));

    expect(await screen.findByAltText("candid.jpg")).toBeInTheDocument();
    expect(screen.getByAltText("portrait.jpg")).toBeInTheDocument();
    expect(screen.getByText(/comparison 1 of 5/i)).toBeInTheDocument();
  });

  it("shows the model's auditable interpretation and guided ranking", async () => {
    route({
      projectId: "project-1",
      status: "completed",
      provider: "groq",
      model: "qwen/qwen3.8-27b",
      summary: "Favor bright, genuine smiles.",
      positiveDescriptors: ["a person smiling"],
      negativeDescriptors: ["a dark underexposed photo"],
      photoNotes: [
        { photoId: "photo-2", originalFilename: "laugh.jpg", effect: "boost", reason: "Wide natural smile." },
      ],
      errorCode: null,
      errorMessage: null,
      rankingBasis: "guided",
      ranking: [
        { photoId: "photo-2", originalFilename: "laugh.jpg", rank: 1, guidedScore: 0.12, briefRelevance: 0.18, explanation: "Closest to \u201ca person smiling\u201d (0.262)." },
        { photoId: "photo-1", originalFilename: "dark.jpg", rank: 2, guidedScore: 0.01, briefRelevance: 0.21, explanation: "Closest to \u201ca person smiling\u201d (0.150)." },
        { photoId: "photo-3", originalFilename: "blur.jpg", rank: 3, guidedScore: -0.02, briefRelevance: 0.1, explanation: "Closest to \u201ca person smiling\u201d (0.100)." },
      ],
    });

    render(<App />);

    expect(await screen.findByText("Favor bright, genuine smiles.")).toBeInTheDocument();
    expect(screen.getByText(/qwen\/qwen3.8-27b via groq/i)).toBeInTheDocument();
    expect(screen.getByText("a person smiling")).toBeInTheDocument();
    expect(screen.getByText("a dark underexposed photo")).toBeInTheDocument();
    expect(screen.getByText("Wide natural smile.")).toBeInTheDocument();
    const leaders = screen.getByRole("list", { name: "Top 2 by AI guidance" });
    expect(leaders).toHaveTextContent(/laugh\.jpg.*dark\.jpg/);
    expect(leaders).not.toHaveTextContent("blur.jpg");
    expect(screen.queryByText(/interpretation unavailable/i)).not.toBeInTheDocument();
  });

  it("labels the degraded fallback and retries the model call", async () => {
    route({
      projectId: "project-1",
      status: "failed",
      provider: "groq",
      model: "qwen/qwen3.8-27b",
      summary: null,
      positiveDescriptors: [],
      negativeDescriptors: [],
      photoNotes: [],
      errorCode: "rate_limited",
      errorMessage: "Groq returned HTTP 429.",
      rankingBasis: "brief_relevance",
      ranking: [
        { photoId: "photo-1", originalFilename: "dark.jpg", rank: 1, guidedScore: null, briefRelevance: 0.21, explanation: null },
      ],
    });

    render(<App />);

    expect(await screen.findByText(/AI interpretation unavailable/i)).toBeInTheDocument();
    expect(screen.getByText(/Groq returned HTTP 429\./)).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Top 1 by basic relevance" })).toHaveTextContent("dark.jpg");
    fireEvent.click(screen.getByRole("button", { name: "Retry AI interpretation" }));
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(
          ([url, init]) => url.endsWith("/projects/project-1/interpretation") && init?.method === "POST",
        ),
      ).toBe(true),
    );
  });
});

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe("proposal step", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    window.localStorage.clear();
  });

  it("stays hidden until analysis has completed", async () => {
    window.localStorage.setItem("selectiq.projectId", "project-1");
    fetchMock.mockResolvedValue(
      response({
        projectId: "project-1",
        acceptedCount: 3,
        remainingCapacity: 27,
        failures: [],
        prompt: "Quiet moments.",
        target: 2,
        analysisStatus: "idle",
        analysisTotal: 3,
        analysisCompleted: 0,
        analysisFailed: 0,
        analysisFailures: [],
      }),
    );
    render(<App />);
    await screen.findByLabelText("3 photos accepted");
    expect(screen.queryByRole("heading", { name: "Generate a proposal" })).not.toBeInTheDocument();
  });
});

describe("guided demo", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    window.localStorage.clear();
  });

  it("shows the six-step demo guide", () => {
    render(<App />);
    const steps = screen.getByRole("list", { name: "Demo steps" });
    expect(steps).toHaveTextContent("Upload 10–30 JPEGs");
    expect(steps).toHaveTextContent("Make 5 A/B choices");
  });

  it("keeps the saved project when the API is temporarily unreachable", async () => {
    window.localStorage.setItem("selectiq.projectId", "project-1");
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent("cannot reach its local API");
    expect(window.localStorage.getItem("selectiq.projectId")).toBe("project-1");
  });

  it("forgets a saved project that no longer exists", async () => {
    window.localStorage.setItem("selectiq.projectId", "project-1");
    fetchMock.mockResolvedValueOnce(response({ detail: "Project project-1 was not found." }, 404));

    render(<App />);

    await waitFor(() => expect(window.localStorage.getItem("selectiq.projectId")).toBeNull());
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

describe("guided demo after reload", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    window.localStorage.clear();
    window.localStorage.setItem("selectiq.projectId", "project-1");
  });

  it("restores saved A/B progress into the step guide", async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (url.endsWith("/status")) {
        return response({
          projectId: "project-1",
          acceptedCount: 18,
          remainingCapacity: 12,
          failures: [],
          prompt: "Peak action.",
          target: 5,
          analysisStatus: "completed",
          analysisTotal: 18,
          analysisCompleted: 18,
          analysisFailed: 0,
          analysisFailures: [],
        });
      }
      if (url.endsWith("/comparisons/next")) {
        return response({ projectId: "project-1", sequence: 6, budget: 5, completed: true, photoA: null, photoB: null });
      }
      if (url.endsWith("/interpretation")) return response({ detail: "unused" }, 404);
      if (url.endsWith("/recommendations")) return response({ detail: "none" }, 404);
      throw new Error(`Unexpected request ${url}`);
    });

    render(<App />);

    const steps = await screen.findByRole("list", { name: "Demo steps" });
    await waitFor(() => expect(steps).toHaveTextContent("Done: 5 of 5 choices"));
  });
});
