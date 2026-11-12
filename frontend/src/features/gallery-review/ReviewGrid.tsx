import { useState } from "react";

import { thumbnailUrl } from "../../shared/api/client";
import type { Recommendation } from "../../shared/types";

type ReviewGridProps = {
  projectId: string;
  recommendations: Recommendation[];
  pendingPhotoId: string | null;
  onRemove: (photoId: string) => void;
  onRestore: (photoId: string) => void;
};

export function ReviewGrid({
  projectId,
  recommendations,
  pendingPhotoId,
  onRemove,
  onRestore,
}: ReviewGridProps) {
  const [preview, setPreview] = useState<Recommendation | null>(null);
  return (
    <><ul className="review-grid" aria-label="Proposed photographs">
      {recommendations.map((item) => {
        const name = item.originalFilename;
        return (
          <li
            key={item.photoId}
            className={item.removed ? "review-card removed" : "review-card"}
            aria-label={item.removed ? `${name}, removed` : `${name}, rank ${item.rank}`}
          >
            <div className="thumb">
              <button className="review-preview" type="button" onClick={() => setPreview(item)} aria-label={`Open ${name}`}>
                <img src={thumbnailUrl(projectId, item.photoId)} alt={name} loading="lazy" />
              </button>
              <span className="rank">{item.rank}</span>
              {item.removed && <span className="removed-badge">Removed</span>}
            </div>
            <div className="card-body">
              <span className="filename" title={name}>
                {name}
              </span>
              <span className="score">score {item.score.toFixed(2)}</span>
            </div>
            {item.removed ? (
              <button
                type="button"
                className="card-action restore"
                onClick={() => onRestore(item.photoId)}
                disabled={pendingPhotoId !== null}
                aria-label={`Undo remove ${name}`}
              >
                Undo
              </button>
            ) : (
              <button
                type="button"
                className="card-action"
                onClick={() => onRemove(item.photoId)}
                disabled={pendingPhotoId !== null}
                aria-label={`Remove ${name}`}
              >
                Remove
              </button>
            )}
          </li>
        );
      })}
    </ul>{preview && (
      <div className="lightbox" role="dialog" aria-modal="true" aria-label={preview.originalFilename}>
        <button className="lightbox-backdrop" type="button" onClick={() => setPreview(null)} aria-label="Close preview" />
        <figure>
          <img src={thumbnailUrl(projectId, preview.photoId)} alt={preview.originalFilename} />
          <figcaption><span>#{preview.rank} · {preview.originalFilename}</span><button type="button" onClick={() => setPreview(null)}>Close</button></figcaption>
        </figure>
      </div>
    )}</>
  );
}
