import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ComparisonPage } from "./ComparisonPage";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

const firstPair = {
  projectId: "project-1",
  sequence: 1,
  budget: 5,
  completed: false,
  photoA: {
    photoId: "photo-a",
    originalFilename: "candid-reaction.jpg",
    imageUrl: "/projects/project-1/photos/photo-a/content",
  },
  photoB: {
    photoId: "photo-b",
    originalFilename: "formal-portrait.jpg",
    imageUrl: "/projects/project-1/photos/photo-b/content",
  },
};

describe("pairwise feedback", () => {
  beforeEach(() => fetchMock.mockReset());

  it("renders exactly two current comparison photos and progress", async () => {
    fetchMock.mockResolvedValueOnce(response(firstPair));

    render(<ComparisonPage projectId="project-1" />);

    const images = await screen.findAllByRole("img");
    expect(images).toHaveLength(2);
    expect(images[0]).toHaveAttribute("alt", "candid-reaction.jpg");
    expect(images[1]).toHaveAttribute("alt", "formal-portrait.jpg");
    expect(screen.getByText(/comparison 1 of 5/i)).toBeInTheDocument();
  });

  it("submits the selected winner and advances to the next pair", async () => {
    const secondPair = {
      ...firstPair,
      sequence: 2,
      photoA: {
        photoId: "photo-c",
        originalFilename: "celebration.jpg",
        imageUrl: "/projects/project-1/photos/photo-c/content",
      },
      photoB: {
        photoId: "photo-d",
        originalFilename: "quiet-moment.jpg",
        imageUrl: "/projects/project-1/photos/photo-d/content",
      },
    };
    fetchMock
      .mockResolvedValueOnce(response(firstPair))
      .mockResolvedValueOnce(
        response({
          projectId: "project-1",
          winnerId: "photo-a",
          loserId: "photo-b",
          sequence: 1,
          completedCount: 1,
          budget: 5,
        }, 201),
      )
      .mockResolvedValueOnce(response(secondPair));
    render(<ComparisonPage projectId="project-1" />);
    await screen.findByAltText("candid-reaction.jpg");

    fireEvent.click(screen.getByRole("button", { name: /prefer candid-reaction.jpg/i }));

    await waitFor(() => expect(screen.getByAltText("celebration.jpg")).toBeInTheDocument());
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "http://localhost:8000/projects/project-1/comparisons",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          photoAId: "photo-a",
          photoBId: "photo-b",
          winnerId: "photo-a",
        }),
      }),
    );
    expect(screen.getByText(/comparison 2 of 5/i)).toBeInTheDocument();
  });

  it("shows a completed state after the fifth saved choice", async () => {
    const finalPair = { ...firstPair, sequence: 5 };
    fetchMock
      .mockResolvedValueOnce(response(finalPair))
      .mockResolvedValueOnce(
        response({
          projectId: "project-1",
          winnerId: "photo-b",
          loserId: "photo-a",
          sequence: 5,
          completedCount: 5,
          budget: 5,
        }, 201),
      )
      .mockResolvedValueOnce(
        response({
          projectId: "project-1",
          sequence: 6,
          budget: 5,
          completed: true,
          photoA: null,
          photoB: null,
        }),
      );
    render(<ComparisonPage projectId="project-1" />);
    await screen.findByAltText("formal-portrait.jpg");

    fireEvent.click(screen.getByRole("button", { name: /prefer formal-portrait.jpg/i }));

    expect(await screen.findByText(/comparison session complete/i)).toBeInTheDocument();
    expect(screen.getByText(/5 of 5 choices complete/i)).toBeInTheDocument();
    expect(screen.queryAllByRole("img")).toHaveLength(0);
  });

  it("shows an informative error when the next pair cannot be loaded", async () => {
    fetchMock.mockResolvedValueOnce(response({ detail: "The comparison could not be loaded." }, 500));

    render(<ComparisonPage projectId="project-1" />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/comparison could not be loaded/i);
  });

  it("keeps the current pair visible and reports an error when saving fails", async () => {
    fetchMock
      .mockResolvedValueOnce(response(firstPair))
      .mockResolvedValueOnce(response({ detail: "The choice could not be saved." }, 500));
    render(<ComparisonPage projectId="project-1" />);
    await screen.findByAltText("candid-reaction.jpg");

    fireEvent.click(screen.getByRole("button", { name: /prefer candid-reaction.jpg/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/choice could not be saved/i);
    expect(screen.getByAltText("candid-reaction.jpg")).toBeInTheDocument();
    expect(screen.getByAltText("formal-portrait.jpg")).toBeInTheDocument();
    expect(screen.getByText(/comparison 1 of 5/i)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("prevents duplicate submissions while a choice is being saved", async () => {
    const pendingSave = deferred<Response>();
    fetchMock
      .mockResolvedValueOnce(response(firstPair))
      .mockReturnValueOnce(pendingSave.promise);
    render(<ComparisonPage projectId="project-1" />);
    await screen.findByAltText("candid-reaction.jpg");
    const winnerButton = screen.getByRole("button", { name: /prefer candid-reaction.jpg/i });

    fireEvent.click(winnerButton);
    fireEvent.click(winnerButton);

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(winnerButton).toBeDisabled();
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
