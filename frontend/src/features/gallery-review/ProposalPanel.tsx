import { useEffect, useState } from "react";

import {
  exportUrl,
  generateProposal,
  getProposal,
  removeFromSelection,
  restoreToSelection,
} from "../../shared/api/client";
import type { Proposal, ProposalProvenance, ProvenanceKind } from "../../shared/types";
import { ReviewGrid } from "./ReviewGrid";

type ProposalPanelProps = {
  projectId: string;
  savedTarget: number | null;
};

export function ProposalPanel({ projectId, savedTarget }: ProposalPanelProps) {
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [pendingPhotoId, setPendingPhotoId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getProposal(projectId)
      .then((existing) => {
        if (!cancelled && existing) setProposal(existing);
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(messageFrom(reason, "The saved proposal could not be loaded."));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  async function generate() {
    setBusy(true);
    setError(null);
    try {
      setProposal(await generateProposal(projectId));
    } catch (reason) {
      setError(messageFrom(reason, "The proposal could not be generated."));
    } finally {
      setBusy(false);
    }
  }

  async function review(photoId: string, action: typeof removeFromSelection) {
    setPendingPhotoId(photoId);
    setError(null);
    try {
      setProposal(await action(projectId, photoId));
    } catch (reason) {
      setError(messageFrom(reason, "The selection could not be updated."));
    } finally {
      setPendingPhotoId(null);
    }
  }

  return (
    <section className="upload-card proposal" aria-labelledby="proposal-title">
      <div className="card-heading">
        <div>
          <h2 id="proposal-title">Generate a proposal</h2>
          <p>SelectIQ ranks every accepted photograph and proposes exactly your target count.</p>
        </div>
      </div>

      <div className="target-row">
        <p className="target-summary">
          {savedTarget === null
            ? "Save your creative brief and target above to generate a proposal."
            : `Target: ${savedTarget} ${savedTarget === 1 ? "photograph" : "photographs"}, from your saved brief.`}
        </p>
        <button
          className="submit"
          type="button"
          onClick={generate}
          disabled={busy || loading || savedTarget === null}
        >
          {busy ? "Generating…" : "Generate proposal"}
        </button>
      </div>
      {proposal && savedTarget !== null && proposal.targetCount !== savedTarget && (
        <p className="hint">
          Your saved target is now {savedTarget}. Generate again to update this proposal.
        </p>
      )}
      {error && <p className="error" role="alert">{error}</p>}

      {proposal && (
        <>
          <ProvenanceNote provenance={proposal.provenance} />
          {proposal.provenance.excludedPhotoCount > 0 && (
            <p className="hint">
              {proposal.provenance.excludedPhotoCount} photographs that failed analysis were not
              considered.
            </p>
          )}
          <div className="selection">
            <span>Proposal version {proposal.version}</span>
            <span>
              {proposal.selectedCount} of {proposal.targetCount} selected
            </span>
          </div>
          <ReviewGrid
            projectId={projectId}
            recommendations={proposal.recommendations}
            pendingPhotoId={pendingPhotoId}
            onRemove={(photoId) => review(photoId, removeFromSelection)}
            onRestore={(photoId) => review(photoId, restoreToSelection)}
          />
          <div className="export-row">
            <p>
              Removed photos are not replaced. The CSV lists each remaining photo's ID and original
              filename.
            </p>
            <a className="submit export" href={exportUrl(projectId)} download>
              Export CSV ({proposal.selectedCount} {proposal.selectedCount === 1 ? "photo" : "photos"})
            </a>
          </div>
        </>
      )}
    </section>
  );
}

const provenanceHeadings: Record<ProvenanceKind, string> = {
  ai_informed: "AI-informed proposal",
  partial_ai: "Partially AI-informed",
  test_signals: "Test signals, not AI",
};

function ProvenanceNote({ provenance }: { provenance: ProposalProvenance }) {
  const choices = provenance.comparisonsUsed;
  return (
    <div role="note" className={`provenance ${provenance.kind}`}>
      <strong>{provenanceHeadings[provenance.kind]}</strong>
      <span>{provenance.label}</span>
      <small>
        Based on {choices} saved {choices === 1 ? "choice" : "choices"}.
      </small>
    </div>
  );
}

function messageFrom(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}
