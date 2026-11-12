import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { FeedbackForm } from "./FeedbackForm";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

describe("A-10 satisfaction feedback", () => {
  beforeEach(() => fetchMock.mockReset());

  it("submits a 1–5 rating and optional comment for the current project", async () => {
    fetchMock.mockResolvedValueOnce(response({
      projectId: "project-1",
      rating: 4,
      comment: "The emotional moments were selected well.",
    }, 201));
    render(<FeedbackForm projectId="project-1" />);

    fireEvent.click(screen.getByRole("radio", { name: "4" }));
    fireEvent.change(screen.getByLabelText("Optional comments"), {
      target: { value: "The emotional moments were selected well." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit feedback" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/projects/project-1/feedback",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          rating: 4,
          comment: "The emotional moments were selected well.",
        }),
      }),
    ));
    expect(await screen.findByText(/feedback saved/i)).toBeInTheDocument();
  });

  it("allows a rating without a comment", async () => {
    fetchMock.mockResolvedValueOnce(response({ projectId: "project-1", rating: 5, comment: null }, 201));
    render(<FeedbackForm projectId="project-1" />);

    fireEvent.click(screen.getByRole("radio", { name: "5" }));
    fireEvent.click(screen.getByRole("button", { name: "Submit feedback" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/projects/project-1/feedback"),
      expect.objectContaining({ body: JSON.stringify({ rating: 5, comment: null }) }),
    ));
  });

  it("requires a rating before submission", () => {
    render(<FeedbackForm projectId="project-1" />);

    fireEvent.click(screen.getByRole("button", { name: "Submit feedback" }));

    expect(screen.getByRole("alert")).toHaveTextContent(/choose a rating/i);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("prevents duplicate requests while feedback is saving", async () => {
    const pending = deferred<Response>();
    fetchMock.mockReturnValueOnce(pending.promise);
    render(<FeedbackForm projectId="project-1" />);
    fireEvent.click(screen.getByRole("radio", { name: "3" }));
    const submit = screen.getByRole("button", { name: "Submit feedback" });

    fireEvent.click(submit);
    fireEvent.click(submit);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(submit).toBeDisabled();
  });

  it("preserves the response and explains an API failure", async () => {
    fetchMock.mockResolvedValueOnce(response({ detail: "Feedback has already been submitted." }, 409));
    render(<FeedbackForm projectId="project-1" />);
    fireEvent.click(screen.getByRole("radio", { name: "2" }));
    fireEvent.change(screen.getByLabelText("Optional comments"), {
      target: { value: "Keep this text" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Submit feedback" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/already been submitted/i);
    expect(screen.getByLabelText("Optional comments")).toHaveValue("Keep this text");
    expect(screen.getByRole("radio", { name: "2" })).toBeChecked();
  });
});

function response(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}
