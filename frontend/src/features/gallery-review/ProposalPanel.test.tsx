import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { jsonResponse as response, proposalFixture, provenanceFixture } from "../../test/fixtures";
import { ProposalPanel } from "./ProposalPanel";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

const noProposal = () => response({ detail: "Project project-1 has no proposal yet." }, 404);

describe("ProposalPanel", () => {
  beforeEach(() => fetchMock.mockReset());

  it("generates a proposal of the saved target size in rank order", async () => {
    fetchMock.mockResolvedValueOnce(noProposal()).mockResolvedValueOnce(response(proposalFixture(), 201));

    render(<ProposalPanel projectId="project-1" savedTarget={5} />);
    expect(await screen.findByText("Target: 5 photographs, from your saved brief.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Generate proposal" }));

    const list = await screen.findByRole("list", { name: "Proposed photographs" });
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(5);
    expect(items[0]).toHaveTextContent("1");
    expect(items[0]).toHaveTextContent("finish.jpg");
    expect(screen.getByText("5 of 5 selected")).toBeInTheDocument();

    const [url, init] = fetchMock.mock.calls[1];
    expect(url).toMatch(/\/projects\/project-1\/recommendations$/);
    expect(init.method).toBe("POST");
    expect(init.body).toBeUndefined();
  });

  it("asks for a saved brief and target before generating", async () => {
    fetchMock.mockResolvedValueOnce(noProposal());
    render(<ProposalPanel projectId="project-1" savedTarget={null} />);

    expect(
      await screen.findByText("Save your creative brief and target above to generate a proposal."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate proposal" })).toBeDisabled();
  });

  it("labels test adapters as not AI", async () => {
    fetchMock.mockResolvedValueOnce(response(proposalFixture()));
    render(<ProposalPanel projectId="project-1" savedTarget={5} />);
    const note = await screen.findByRole("note");
    expect(note).toHaveTextContent("Test signals, not AI");
    expect(note).toHaveTextContent("deterministic-test");
    expect(note).not.toHaveTextContent("AI-informed proposal");
  });

  it("labels genuine CLIP, Groq, and saved choices as AI-informed", async () => {
    fetchMock.mockResolvedValueOnce(
      response(
        proposalFixture({
          isGenuineAi: true,
          provenance: provenanceFixture({
            kind: "ai_informed",
            label: "AI-informed proposal: ViT-B-32 / laion2b_s34b_b79k brief relevance, groq / qwen/qwen3.8-27b guidance, and 5 saved choices.",
            embeddingsGenuine: true,
            guidanceGenuine: true,
          }),
        }),
      ),
    );
    render(<ProposalPanel projectId="project-1" savedTarget={5} />);
    const note = await screen.findByRole("note");
    expect(note).toHaveTextContent("AI-informed proposal");
    expect(note).toHaveTextContent("Based on 5 saved choices");
  });

  it("says when AI interpretation was unavailable", async () => {
    fetchMock.mockResolvedValueOnce(
      response(
        proposalFixture({
          provenance: provenanceFixture({
            kind: "partial_ai",
            label: "Partially AI-informed: ViT-B-32 / laion2b_s34b_b79k brief relevance and 5 saved choices; AI interpretation unavailable — using basic relevance.",
            embeddingsGenuine: true,
            guidanceStatus: "failed",
          }),
        }),
      ),
    );
    render(<ProposalPanel projectId="project-1" savedTarget={5} />);
    const note = await screen.findByRole("note");
    expect(note).toHaveTextContent("Partially AI-informed");
    expect(note).toHaveTextContent("using basic relevance");
  });

  it("warns that photos which failed analysis were left out", async () => {
    fetchMock.mockResolvedValueOnce(
      response(proposalFixture({ provenance: provenanceFixture({ excludedPhotoCount: 2 }) })),
    );
    render(<ProposalPanel projectId="project-1" savedTarget={5} />);
    expect(
      await screen.findByText("2 photographs that failed analysis were not considered."),
    ).toBeInTheDocument();
  });

  it("restores the latest proposal", async () => {
    fetchMock.mockResolvedValueOnce(response(proposalFixture({ version: 2 })));
    render(<ProposalPanel projectId="project-1" savedTarget={5} />);
    expect(await screen.findByText("Proposal version 2")).toBeInTheDocument();
  });

  it("points out when the saved target no longer matches the proposal", async () => {
    fetchMock.mockResolvedValueOnce(response(proposalFixture()));
    render(<ProposalPanel projectId="project-1" savedTarget={7} />);
    expect(
      await screen.findByText("Your saved target is now 7. Generate again to update this proposal."),
    ).toBeInTheDocument();
  });

  it("shows informative server errors", async () => {
    fetchMock
      .mockResolvedValueOnce(noProposal())
      .mockResolvedValueOnce(response({ detail: "Analyze the gallery before generating a proposal." }, 422));
    render(<ProposalPanel projectId="project-1" savedTarget={5} />);
    await screen.findByText("Target: 5 photographs, from your saved brief.");

    fireEvent.click(screen.getByRole("button", { name: "Generate proposal" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Analyze the gallery before generating a proposal.");
    expect(screen.queryByRole("list", { name: "Proposed photographs" })).not.toBeInTheDocument();
  });
});
