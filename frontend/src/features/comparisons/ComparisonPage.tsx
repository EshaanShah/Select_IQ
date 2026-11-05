import { useEffect, useState } from "react";

const apiBaseUrl = import.meta.env.VITE_SELECTIQ_API_URL ?? "http://localhost:8000";

type ComparisonPhoto = {
  photoId: string;
  originalFilename: string;
  imageUrl: string;
};

type NextComparison = {
  projectId: string;
  sequence: number;
  budget: number;
  completed: boolean;
  photoA: ComparisonPhoto | null;
  photoB: ComparisonPhoto | null;
};

export type ComparisonProgress = { completed: number; budget: number; done: boolean };

type ComparisonPageProps = {
  projectId: string;
  onProgress?: (progress: ComparisonProgress) => void;
};

export function ComparisonPage({ projectId, onProgress }: ComparisonPageProps) {
  const [comparison, setComparison] = useState<NextComparison | null>(null);

  useEffect(() => {
    if (!comparison || !onProgress) return;
    onProgress({
      completed: comparison.completed ? comparison.budget : comparison.sequence - 1,
      budget: comparison.budget,
      done: comparison.completed,
    });
  }, [comparison, onProgress]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    loadNext(projectId)
      .then((result) => {
        if (!cancelled) setComparison(result);
      })
      .catch((reason) => {
        if (!cancelled) setError(errorMessage(reason, "The comparison could not be loaded."));
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  async function choose(winnerId: string) {
    if (saving || !comparison?.photoA || !comparison.photoB) return;
    setSaving(true);
    setError(null);
    try {
      await request(`/projects/${projectId}/comparisons`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          photoAId: comparison.photoA.photoId,
          photoBId: comparison.photoB.photoId,
          winnerId,
        }),
      });
      setComparison(await loadNext(projectId));
    } catch (reason) {
      setError(errorMessage(reason, "The choice could not be saved."));
    } finally {
      setSaving(false);
    }
  }

  if (comparison?.completed) {
    return (
      <section className="comparison-card" aria-live="polite">
        <p className="section-kicker">04 · Refine</p>
        <h2>Comparison session complete</h2>
        <p>{comparison.budget} of {comparison.budget} choices complete</p>
      </section>
    );
  }

  return (
    <section className="comparison-card" aria-labelledby="comparison-title">
      <p className="section-kicker">04 · Refine</p>
      <h2 id="comparison-title">Choose the stronger photograph</h2>
      {comparison && <p>Comparison {comparison.sequence} of {comparison.budget}</p>}
      {error && <p className="error" role="alert">{error}</p>}
      {comparison?.photoA && comparison.photoB && (
        <div className="comparison-grid">
          {[comparison.photoA, comparison.photoB].map((photo) => (
            <article key={photo.photoId}>
              <img
                src={`${apiBaseUrl}${photo.imageUrl}`}
                alt={photo.originalFilename}
              />
              <button
                type="button"
                disabled={saving}
                onClick={() => choose(photo.photoId)}
              >
                Prefer {photo.originalFilename}
              </button>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

async function loadNext(projectId: string): Promise<NextComparison> {
  return request<NextComparison>(`/projects/${projectId}/comparisons/next`);
}

async function request<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, init);
  const payload = (await response.json()) as T & { detail?: string };
  if (!response.ok) throw new Error(payload.detail ?? "The SelectIQ request failed.");
  return payload;
}

function errorMessage(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}
