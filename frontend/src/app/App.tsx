import { ChangeEvent, useEffect, useRef, useState } from "react";

import {
  createProject,
  getProjectStatus,
  savePromptAndTarget,
  uploadPhotos,
} from "../shared/api/client";
import type { ImportFailure } from "../shared/types";
import "./app.css";

const projectStorageKey = "selectiq.projectId";
const galleryCapacity = 30;

export function App() {
  const folderInput = useRef<HTMLInputElement>(null);
  const projectToRestore = useRef(window.localStorage.getItem(projectStorageKey));
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [projectId, setProjectId] = useState<string | null>(() =>
    window.localStorage.getItem(projectStorageKey),
  );
  const [acceptedCount, setAcceptedCount] = useState(0);
  const [failures, setFailures] = useState<ImportFailure[]>([]);
  const [batchSummary, setBatchSummary] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [prompt, setPrompt] = useState("");
  const [target, setTarget] = useState("");
  const [briefBusy, setBriefBusy] = useState(false);
  const [briefError, setBriefError] = useState<string | null>(null);
  const [briefSaved, setBriefSaved] = useState(false);

  useEffect(() => {
    folderInput.current?.setAttribute("webkitdirectory", "");
  }, []);

  useEffect(() => {
    if (!projectId || projectId !== projectToRestore.current) return;
    let cancelled = false;
    getProjectStatus(projectId)
      .then((status) => {
        if (!cancelled) {
          setAcceptedCount(status.acceptedCount);
          setFailures(status.failures);
          setPrompt(status.prompt ?? "");
          setTarget(status.target?.toString() ?? "");
        }
      })
      .catch(() => {
        if (!cancelled) {
          window.localStorage.removeItem(projectStorageKey);
          setProjectId(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  function chooseFiles(event: ChangeEvent<HTMLInputElement>) {
    setSelectedFiles(Array.from(event.target.files ?? []));
    setBatchSummary(null);
    setError(null);
  }

  async function submitGallery() {
    if (selectedFiles.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      let activeProjectId = projectId;
      if (!activeProjectId) {
        const project = await createProject();
        activeProjectId = project.projectId;
        window.localStorage.setItem(projectStorageKey, activeProjectId);
        setProjectId(activeProjectId);
      }
      const result = await uploadPhotos(activeProjectId, selectedFiles);
      setAcceptedCount(result.acceptedCount);
      setFailures((current) => [...current, ...result.rejected]);
      setBatchSummary(
        `${result.batchAcceptedCount} accepted, ${result.batchRejectedCount} rejected in this upload.`,
      );
      setSelectedFiles([]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The gallery could not be uploaded.");
    } finally {
      setBusy(false);
    }
  }

  async function submitPromptAndTarget() {
    setBriefError(null);
    setBriefSaved(false);
    if (!prompt.trim()) {
      setBriefError("Enter a creative brief; the brief cannot be blank.");
      return;
    }
    if (!/^\d+$/.test(target)) {
      setBriefError("Target must be a positive whole number.");
      return;
    }
    const numericTarget = Number(target);
    if (numericTarget < 1) {
      setBriefError("Target must be at least 1.");
      return;
    }
    if (numericTarget > acceptedCount) {
      setBriefError(`Target cannot exceed the ${acceptedCount} accepted photos.`);
      return;
    }
    if (!projectId) {
      setBriefError("Create a project and upload photographs before saving your brief.");
      return;
    }
    setBriefBusy(true);
    try {
      const result = await savePromptAndTarget(projectId, prompt, numericTarget);
      setPrompt(result.prompt);
      setTarget(result.target.toString());
      setBriefSaved(true);
    } catch (reason) {
      setBriefError(reason instanceof Error ? reason.message : "The brief could not be saved.");
    } finally {
      setBriefBusy(false);
    }
  }

  const remaining = Math.max(galleryCapacity - acceptedCount, 0);

  return (
    <main className="shell">
      <header className="hero">
        <p className="eyebrow">SelectIQ Alpha</p>
        <h1>Import your gallery</h1>
        <p className="lede">
          Add JPEG photographs for curation. SelectIQ stores private working copies and never
          changes your originals.
        </p>
      </header>

      <section className="upload-card" aria-labelledby="upload-title">
        <div className="card-heading">
          <div>
            <h2 id="upload-title">Choose photographs</h2>
            <p>JPG or JPEG · 25 MB and 60 megapixels per photograph</p>
          </div>
          <div
            className="count"
            aria-live="polite"
            aria-label={`${acceptedCount} photos accepted`}
          >
            <strong>{acceptedCount}</strong>
            <span>photos accepted</span>
          </div>
        </div>

        <div className="pickers">
          <label className="picker">
            Choose files
            <input
              type="file"
              accept=".jpg,.jpeg,image/jpeg"
              multiple
              onChange={chooseFiles}
              disabled={busy || remaining === 0}
            />
          </label>
          <label className="picker secondary">
            Choose folder
            <input
              ref={folderInput}
              type="file"
              accept=".jpg,.jpeg,image/jpeg"
              multiple
              onChange={chooseFiles}
              disabled={busy || remaining === 0}
            />
          </label>
        </div>

        <div className="selection" aria-live="polite">
          <span>{selectedFiles.length} files selected</span>
          <span>{remaining} spaces remaining</span>
        </div>

        <button
          className="submit"
          type="button"
          onClick={submitGallery}
          disabled={busy || selectedFiles.length === 0 || remaining === 0}
        >
          {busy ? "Importing…" : "Import selected photographs"}
        </button>

        {batchSummary && <p className="success">{batchSummary}</p>}
        {error && <p className="error" role="alert">{error}</p>}
      </section>

      {failures.length > 0 && (
        <section className="failures" aria-labelledby="failures-title">
          <h2 id="failures-title">Files that need attention</h2>
          <ul>
            {failures.map((failure, index) => (
              <li key={`${failure.filename}-${failure.code}-${index}`}>
                <strong>{failure.filename}</strong>
                <span>{failure.message}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {acceptedCount > 0 && (
        <>
          <section className="ready" aria-live="polite">
            <span aria-hidden="true">✓</span>
            <div>
              <strong>Your gallery is ready for the next step.</strong>
              <p>Analysis has not started. You can add more photographs first.</p>
            </div>
          </section>

          <section className="brief-card" aria-labelledby="brief-title">
            <h2 id="brief-title">Describe your creative intent</h2>
            <p className="brief-help">
              Tell SelectIQ which story, mood, subjects, and moments should shape the collection.
            </p>
            <label className="field">
              <span>Creative brief</span>
              <textarea
                value={prompt}
                onChange={(event) => {
                  setPrompt(event.target.value);
                  setBriefSaved(false);
                }}
                disabled={briefBusy}
                rows={5}
              />
            </label>
            <div className="field target-field">
              <label htmlFor="target-count">Target number of photographs</label>
              <input
                id="target-count"
                type="number"
                min="1"
                max={acceptedCount}
                step="1"
                value={target}
                onChange={(event) => {
                  setTarget(event.target.value);
                  setBriefSaved(false);
                }}
                disabled={briefBusy}
              />
              <small>Choose between 1 and {acceptedCount}.</small>
            </div>
            <button
              className="submit"
              type="button"
              onClick={submitPromptAndTarget}
              disabled={briefBusy}
            >
              {briefBusy ? "Saving…" : "Save brief and target"}
            </button>
            {briefSaved && <p className="success">Brief and target saved.</p>}
            {briefError && <p className="error" role="alert">{briefError}</p>}
          </section>
        </>
      )}
    </main>
  );
}
