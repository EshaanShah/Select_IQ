import type { ComparisonProgress } from "../comparisons/ComparisonPage";
import type { AnalysisStatus } from "../../shared/types";

export type { ComparisonProgress };
export type ProposalProgress = { selected: number; target: number };

export type GuidedStepsProps = {
  acceptedCount: number;
  savedTarget: number | null;
  analysisStatus: AnalysisStatus;
  comparisons: ComparisonProgress | null;
  proposal: ProposalProgress | null;
};

type Step = {
  title: string;
  done: boolean;
  doneDetail?: string;
  currentDetail?: string;
};

const alphaMinimum = 10;
const alphaMaximum = 30;

export function GuidedSteps({
  acceptedCount,
  savedTarget,
  analysisStatus,
  comparisons,
  proposal,
}: GuidedStepsProps) {
  const steps: Step[] = [
    { title: "Upload 10–30 JPEGs", done: acceptedCount > 0, doneDetail: uploadDetail(acceptedCount) },
    { title: "Save brief and target", done: savedTarget !== null, doneDetail: `Done: target ${savedTarget}` },
    {
      title: "Run AI analysis",
      done: analysisStatus === "completed",
      currentDetail: analysisDetail(analysisStatus),
    },
    {
      title: "Make 5 A/B choices",
      done: Boolean(comparisons?.done),
      doneDetail: comparisons ? `Done: ${comparisons.completed} of ${comparisons.budget} choices` : undefined,
      currentDetail: comparisons ? `${comparisons.completed} of ${comparisons.budget} choices` : undefined,
    },
    { title: "Generate proposal", done: proposal !== null },
    {
      title: "Remove and export",
      done: false,
      currentDetail: proposal ? `${proposal.selected} of ${proposal.target} selected` : undefined,
    },
  ];
  const currentIndex = steps.findIndex((step) => !step.done);
  const completedCount = steps.filter((step) => step.done).length;

  return (
    <section className="guided-steps" aria-labelledby="workflow-title">
      <div className="workflow-heading">
        <div>
          <p className="section-kicker">Guided workflow</p>
          <h2 id="workflow-title">From contact sheet to final selection</h2>
        </div>
        <div className="workflow-progress" aria-label={`${completedCount} of 6 steps complete`}>
          <strong>{completedCount}<span>/6</span></strong>
          <small>steps complete</small>
        </div>
      </div>
      <nav aria-label="Demo progress">
        <ol aria-label="Demo steps">
          {steps.map((step, index) => {
            const state = step.done ? "done" : index === currentIndex ? "current" : "upcoming";
            const detail =
              state === "done"
                ? (step.doneDetail ?? "Done")
                : state === "current"
                  ? (step.currentDetail ?? "Current")
                  : "Next";
            return (
              <li
                key={step.title}
                className={`step ${state}`}
                aria-current={state === "current" ? "step" : undefined}
              >
                <span className="step-number" aria-hidden="true">
                  {state === "done" ? "✓" : index + 1}
                </span>
                <span className="step-text">
                  <strong>{step.title}</strong>
                  <small>{detail}</small>
                </span>
              </li>
            );
          })}
        </ol>
      </nav>
    </section>
  );
}

function uploadDetail(count: number): string {
  const inRange = count >= alphaMinimum && count <= alphaMaximum;
  return `Done: ${count} photos${inRange ? "" : ` (${alphaMinimum}–${alphaMaximum} recommended)`}`;
}

function analysisDetail(status: AnalysisStatus): string | undefined {
  switch (status) {
    case "queued":
    case "running":
      return "Running…";
    case "partial_failure":
    case "failed":
      return "Needs attention";
    case "idle":
    case "completed":
      return undefined;
    default: {
      const unhandled: never = status;
      return unhandled;
    }
  }
}
