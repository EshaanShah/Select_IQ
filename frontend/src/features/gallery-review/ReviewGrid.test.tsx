import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { jsonResponse as response, proposalFixture, withRemoved } from "../../test/fixtures";
import { ProposalPanel } from "./ProposalPanel";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

async function renderWithProposal(proposal = proposalFixture()) {
  fetchMock.mockResolvedValueOnce(response(proposal));
  render(<ProposalPanel projectId="project-1" savedTarget={5} />);
  return screen.findByRole("list", { name: "Proposed photographs" });
}

describe("proposal review grid", () => {
  beforeEach(() => fetchMock.mockReset());

  it("shows every proposed photo as a thumbnail card", async () => {
    const grid = await renderWithProposal();
    const cards = within(grid).getAllByRole("listitem");
    expect(cards).toHaveLength(5);
    const image = within(cards[0]).getByRole("img", { name: "finish.jpg" });
    expect(image.getAttribute("src")).toMatch(/\/projects\/project-1\/photos\/photo-0\/thumbnail$/);
    expect(image).toHaveAttribute("loading", "lazy");
  });

  it("removes a suggestion without adding a replacement", async () => {
    const grid = await renderWithProposal();
    fetchMock.mockResolvedValueOnce(response(withRemoved(proposalFixture(), ["photo-1"])));

    fireEvent.click(within(grid).getByRole("button", { name: "Remove start.jpg" }));

    expect(await screen.findByText("4 of 5 selected")).toBeInTheDocument();
    expect(within(grid).getAllByRole("listitem")).toHaveLength(5);
    const removedCard = within(grid).getByRole("listitem", { name: /start\.jpg, removed/ });
    expect(within(removedCard).getByRole("button", { name: "Undo remove start.jpg" })).toBeInTheDocument();
    const [url, init] = fetchMock.mock.calls[1];
    expect(url).toMatch(/\/projects\/project-1\/recommendations\/selection\/photo-1$/);
    expect(init.method).toBe("DELETE");
  });

  it("undoes a removal", async () => {
    const grid = await renderWithProposal(withRemoved(proposalFixture(), ["photo-1"]));
    fetchMock.mockResolvedValueOnce(response(proposalFixture()));

    fireEvent.click(within(grid).getByRole("button", { name: "Undo remove start.jpg" }));

    expect(await screen.findByText("5 of 5 selected")).toBeInTheDocument();
    const [url, init] = fetchMock.mock.calls[1];
    expect(url).toMatch(/\/selection\/photo-1\/restore$/);
    expect(init.method).toBe("POST");
  });

  it("allows removing every suggestion and still exporting", async () => {
    const all = proposalFixture().recommendations.map((item) => item.photoId);
    await renderWithProposal(withRemoved(proposalFixture(), all));
    expect(screen.getByText("0 of 5 selected")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Export CSV (0 photos)" })).toBeInTheDocument();
  });

  it("links the export to the remaining-filename CSV", async () => {
    await renderWithProposal(withRemoved(proposalFixture(), ["photo-2"]));
    const link = screen.getByRole("link", { name: "Export CSV (4 photos)" });
    expect(link.getAttribute("href")).toMatch(/\/projects\/project-1\/recommendations\/export$/);
    expect(link).toHaveAttribute("download");
  });

  it("explains failed removals", async () => {
    const grid = await renderWithProposal();
    fetchMock.mockResolvedValueOnce(response({ detail: "Photo photo-1 is not part of proposal version 1." }, 404));

    fireEvent.click(within(grid).getByRole("button", { name: "Remove start.jpg" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("not part of proposal version 1");
    expect(screen.getByText("5 of 5 selected")).toBeInTheDocument();
  });
});
