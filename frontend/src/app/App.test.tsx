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
    expect(screen.getByText(/ready for the next step/i)).toBeInTheDocument();
  });

  it("restores an existing project's accepted count", async () => {
    window.localStorage.setItem("selectiq.projectId", "project-1");
    fetchMock.mockResolvedValueOnce(
      response({ projectId: "project-1", acceptedCount: 14, remainingCapacity: 286, failures: [] }),
    );

    render(<App />);

    await waitFor(() => expect(screen.getByLabelText("14 photos accepted")).toBeInTheDocument());
    expect(screen.getByText("286 spaces remaining")).toBeInTheDocument();
  });
});

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}
