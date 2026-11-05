import { useEffect, useState } from "react";

import { getInterpretation, startInterpretation } from "../../shared/api/client";
import type { Interpretation } from "../../shared/types";

type Props = {
  projectId: string;
  target: number | null;
};

const pollMs = 1000;

export function InterpretationPanel({ projectId, target }: Props) {
  const [interpretation, setInterpretation] = useState<Interpretation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;
    const load = () => {
      getInterpretation(projectId)
        .then((result) => {
          if (cancelled) return;
          setInterpretation(result);
          setError(null);
          if (result.status === "running") timer = window.setTimeout(load, pollMs);
        })
        .catch((reason) => {
          if (!cancelled) {
            setError(reason instanceof Error ? reason.message : "Interpretation could not load.");
          }
        });
    };
    load();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [projectId, refresh]);

  async function interpret() {
    setBusy(true);
    setError(null);
    try {
      await startInterpretation(projectId);
      setRefresh((value) => value + 1);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Interpretation could not start.");
    } finally {
      setBusy(false);
    }
  }

  if (!interpretation) {
    return error ? (
      <section className="interpretation-card">
        <p className="section-kicker">AI reading</p>
        <h2>AI brief interpretation</h2>
        <p className="error" role="alert">{error}</p>
      </section>
    ) : null;
  }

  const { status } = interpretation;
  const guided = interpretation.rankingBasis === "guided";
  const shown = interpretation.ranking.slice(0, target ?? 5);
  const listLabel = `Top ${shown.length} by ${guided ? "AI guidance" : "basic relevance"}`;
  const modelLabel =
    interpretation.model && interpretation.provider
      ? `${interpretation.model} via ${interpretation.provider}`
      : null;

  return (
    <section className="interpretation-card" aria-live="polite">
      <div>
        <p className="section-kicker">AI reading</p>
        <h2>AI brief interpretation</h2>
        {status === "running" && <p>Interpreting your brief against the gallery…</p>}
        {status === "not_started" && (
          <p>The generative model has not interpreted this brief yet.</p>
        )}
        {status === "completed" && (
          <>
            <p className="interpretation-summary">{interpretation.summary}</p>
            {modelLabel && <p className="interpretation-meta">Interpreted by {modelLabel}.</p>}
          </>
        )}
        {status === "failed" && (
          <p className="degraded" role="alert">
            <strong>AI interpretation unavailable — using basic relevance.</strong>{" "}
            {interpretation.errorMessage}
          </p>
        )}
        {error && <p className="error" role="alert">{error}</p>}
      </div>

      {status === "completed" && (
        <div className="descriptor-groups">
          <DescriptorList title="Favor" items={interpretation.positiveDescriptors} tone="favor" />
          <DescriptorList title="Avoid" items={interpretation.negativeDescriptors} tone="avoid" />
        </div>
      )}

      {status === "completed" && interpretation.photoNotes.length > 0 && (
        <div>
          <h3>Model notes on specific photographs</h3>
          <ul className="photo-notes">
            {interpretation.photoNotes.map((note) => (
              <li key={note.photoId}>
                <span className={`note-effect ${note.effect}`}>{note.effect}</span>
                <strong>{note.originalFilename}</strong>
                <span>{note.reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {shown.length > 0 && status !== "running" && (
        <div>
          <h3>{listLabel}</h3>
          <ol className="ranking" aria-label={listLabel}>
            {shown.map((entry) => (
              <li key={entry.photoId}>
                <strong>{entry.originalFilename}</strong>
                <span className="scores">
                  {guided && entry.guidedScore !== null && `guided ${entry.guidedScore.toFixed(3)} · `}
                  {entry.briefRelevance !== null && `brief ${entry.briefRelevance.toFixed(3)}`}
                </span>
                {entry.explanation && <span className="explanation">{entry.explanation}</span>}
              </li>
            ))}
          </ol>
        </div>
      )}

      {(status === "failed" || status === "not_started") && (
        <button className="submit" type="button" onClick={interpret} disabled={busy}>
          {status === "failed" ? "Retry AI interpretation" : "Interpret brief"}
        </button>
      )}
    </section>
  );
}

function DescriptorList({
  title,
  items,
  tone,
}: {
  title: string;
  items: string[];
  tone: "favor" | "avoid";
}) {
  if (items.length === 0) return null;
  return (
    <div>
      <h3>{title}</h3>
      <ul className={`descriptors ${tone}`}>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
