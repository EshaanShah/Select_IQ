import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { GuidedSteps, type GuidedStepsProps } from "./GuidedSteps";

const start: GuidedStepsProps = {
  acceptedCount: 0,
  savedTarget: null,
  analysisStatus: "idle",
  comparisons: null,
  proposal: null,
};

function steps() {
  return within(screen.getByRole("list", { name: "Demo steps" })).getAllByRole("listitem");
}

function current() {
  return steps().filter((item) => item.getAttribute("aria-current") === "step");
}

describe("GuidedSteps", () => {
  it("lists the six Alpha steps and starts at upload", () => {
    render(<GuidedSteps {...start} />);
    expect(steps().map((item) => item.querySelector("strong")?.textContent)).toEqual([
      "Upload 10–30 JPEGs",
      "Save brief and target",
      "Run AI analysis",
      "Make 5 A/B choices",
      "Generate proposal",
      "Remove and export",
    ]);
    expect(current()).toHaveLength(1);
    expect(current()[0]).toHaveTextContent("Upload 10–30 JPEGs");
  });

  it("moves through brief and analysis", () => {
    const { rerender } = render(<GuidedSteps {...start} acceptedCount={18} />);
    expect(steps()[0]).toHaveTextContent("Done: 18 photos");
    expect(current()[0]).toHaveTextContent("Save brief and target");

    rerender(<GuidedSteps {...start} acceptedCount={18} savedTarget={5} analysisStatus="running" />);
    expect(steps()[1]).toHaveTextContent("Done: target 5");
    expect(current()[0]).toHaveTextContent("Run AI analysis");
    expect(current()[0]).toHaveTextContent("Running…");
  });

  it("flags failed analysis as needing attention", () => {
    render(<GuidedSteps {...start} acceptedCount={18} savedTarget={5} analysisStatus="partial_failure" />);
    expect(current()[0]).toHaveTextContent("Needs attention");
  });

  it("tracks A/B progress, then the proposal and export", () => {
    const analyzed = { ...start, acceptedCount: 18, savedTarget: 5, analysisStatus: "completed" as const };
    const { rerender } = render(
      <GuidedSteps {...analyzed} comparisons={{ completed: 2, budget: 5, done: false }} />,
    );
    expect(current()[0]).toHaveTextContent("Make 5 A/B choices");
    expect(current()[0]).toHaveTextContent("2 of 5 choices");

    rerender(<GuidedSteps {...analyzed} comparisons={{ completed: 5, budget: 5, done: true }} />);
    expect(steps()[3]).toHaveTextContent("Done: 5 of 5 choices");
    expect(current()[0]).toHaveTextContent("Generate proposal");

    rerender(
      <GuidedSteps
        {...analyzed}
        comparisons={{ completed: 5, budget: 5, done: true }}
        proposal={{ selected: 4, target: 5 }}
      />,
    );
    expect(steps()[4]).toHaveTextContent("Done");
    expect(current()[0]).toHaveTextContent("Remove and export");
    expect(current()[0]).toHaveTextContent("4 of 5 selected");
  });

  it("notes when the gallery is below the recommended Alpha size", () => {
    render(<GuidedSteps {...start} acceptedCount={4} />);
    expect(steps()[0]).toHaveTextContent("Done: 4 photos (10–30 recommended)");
  });
});
