import { useEffect, useState } from "react";

import { thumbnailUrl } from "../api/client";
import type { AcceptedPhoto } from "../types";

type PreviewPhoto = Pick<AcceptedPhoto, "photoId" | "originalFilename" | "state"> & {
  src: string;
  error?: string | null;
};

type Props = {
  projectId: string | null;
  photos: AcceptedPhoto[];
  pendingFiles?: File[];
  compact?: boolean;
};

const noPendingFiles: File[] = [];

export function PhotoGallery({ projectId, photos, pendingFiles = noPendingFiles, compact = false }: Props) {
  const [pending, setPending] = useState<PreviewPhoto[]>([]);
  const [active, setActive] = useState<PreviewPhoto | null>(null);

  useEffect(() => {
    if (typeof URL.createObjectURL !== "function") return;
    const previews = pendingFiles.map((file, index) => ({
      photoId: `pending-${index}`,
      originalFilename: file.name,
      state: "pending" as const,
      src: URL.createObjectURL(file),
    }));
    setPending(previews);
    return () => previews.forEach((photo) => URL.revokeObjectURL(photo.src));
  }, [pendingFiles]);

  const restored: PreviewPhoto[] = projectId
    ? photos.map((photo) => ({
        photoId: photo.photoId,
        originalFilename: photo.originalFilename,
        state: photo.state,
        src: photo.thumbnailUrl?.startsWith("http")
          ? photo.thumbnailUrl
          : thumbnailUrl(projectId, photo.photoId),
        error: photo.analysisErrorMessage,
      }))
    : [];
  const items = pending.length > 0 ? pending : restored;

  if (items.length === 0) {
    return (
      <div className="gallery-empty" aria-label="Empty gallery preview">
        <span aria-hidden="true">▧</span>
        <strong>Your contact sheet will appear here</strong>
        <p>Select JPEGs to preview the story before importing.</p>
      </div>
    );
  }

  return (
    <>
      <ul className={compact ? "photo-gallery compact" : "photo-gallery"} aria-label="Gallery previews">
        {items.map((photo, index) => (
          <li key={photo.photoId} className={`photo-tile ${photo.state}`}>
            <button type="button" onClick={() => setActive(photo)} aria-label={`Open ${photo.originalFilename}`}>
              <img src={photo.src} alt={photo.originalFilename} loading="lazy" />
              <span className="photo-shade" />
              <span className="photo-index">{String(index + 1).padStart(2, "0")}</span>
              <span className="photo-name">{photo.originalFilename}</span>
              {photo.state === "processing" && <span className="photo-state">Analyzing</span>}
              {photo.state === "completed" && <span className="photo-state complete">Ready</span>}
              {photo.state === "failed" && <span className="photo-state failed">Needs attention</span>}
            </button>
          </li>
        ))}
      </ul>
      {active && (
        <div className="lightbox" role="dialog" aria-modal="true" aria-label={active.originalFilename}>
          <button className="lightbox-backdrop" type="button" onClick={() => setActive(null)} aria-label="Close preview" />
          <figure>
            <img src={active.src} alt={active.originalFilename} />
            <figcaption>
              <span>{active.originalFilename}</span>
              <button type="button" onClick={() => setActive(null)}>Close</button>
            </figcaption>
            {active.error && <p className="error">{active.error}</p>}
          </figure>
        </div>
      )}
    </>
  );
}
