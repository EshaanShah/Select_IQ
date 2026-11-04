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
  return (
    <ul className="review-grid" aria-label="Proposed photographs">
      {recommendations.map((item) => {
        const name = item.originalFilename;
        return (
          <li
            key={item.photoId}
            className={item.removed ? "review-card removed" : "review-card"}
            aria-label={item.removed ? `${name}, removed` : `${name}, rank ${item.rank}`}
          >
            <div className="thumb">
              <img src={thumbnailUrl(projectId, item.photoId)} alt={name} loading="lazy" />
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
    </ul>
  );
}
