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

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}
