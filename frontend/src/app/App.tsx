import { ChangeEvent, useEffect, useRef, useState } from "react";

import { createProject, getProjectStatus, startAnalysis, uploadPhotos } from "../shared/api/client";
import type { AnalysisFailure, AnalysisStatus, ImportFailure, ProjectStatus } from "../shared/types";
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
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus>("idle");
  const [analysisCompleted, setAnalysisCompleted] = useState(0);
  const [analysisFailures, setAnalysisFailures] = useState<AnalysisFailure[]>([]);
  const [analysisModel, setAnalysisModel] = useState<string | null>(null);

  function applyStatus(status: ProjectStatus) {
    setAcceptedCount(status.acceptedCount);
    setFailures(status.failures);
    setAnalysisStatus((current) =>
      status.analysisStatus === "idle" && current === "queued" ? current : (status.analysisStatus ?? "idle"),
    );
    setAnalysisCompleted(status.analysisCompleted ?? 0);
    setAnalysisFailures(status.analysisFailures ?? []);
    setAnalysisModel(status.analysisModel ?? null);
  }

  useEffect(() => {
    folderInput.current?.setAttribute("webkitdirectory", "");
  }, []);

  useEffect(() => {
    if (!projectId || projectId !== projectToRestore.current) return;
    let cancelled = false;
    getProjectStatus(projectId)
      .then((status) => {
        if (!cancelled) {
          applyStatus(status);
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

  useEffect(() => {
    if (!projectId || !["queued", "running"].includes(analysisStatus)) return;
    let cancelled = false;
    const timer = window.setInterval(() => {
      getProjectStatus(projectId)
        .then((status) => {
          if (!cancelled) applyStatus(status);
        })
        .catch((reason) => {
          if (!cancelled) setError(reason instanceof Error ? reason.message : "Analysis status could not be loaded.");
        });
    }, 1000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [analysisStatus, projectId]);

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
      setAnalysisStatus("idle");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The gallery could not be uploaded.");
    } finally {
      setBusy(false);
    }
  }

  async function analyzeGallery() {
    if (!projectId) return;
    setBusy(true);
    setError(null);
    try {
      const result = await startAnalysis(projectId);
      setAnalysisStatus(result.analysisStatus);
      if (result.analysisStatus === "completed") {
        applyStatus(await getProjectStatus(projectId));
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Analysis could not be started.");
    } finally {
      setBusy(false);
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
        <section className="analysis-card" aria-live="polite">
          <div>
            <h2>AI feature analysis</h2>
            {analysisStatus === "idle" && <p>Generate visual embeddings before continuing.</p>}
            {["queued", "running"].includes(analysisStatus) && (
              <p>{analysisCompleted} of {acceptedCount} photographs analyzed…</p>
            )}
            {analysisStatus === "completed" && (
              <p><strong>Your gallery is ready for the next step.</strong>{analysisModel ? ` ${analysisModel} completed the analysis.` : ""}</p>
            )}
            {["partial_failure", "failed"].includes(analysisStatus) && (
              <p className="error" role="alert">Analysis failed for {analysisFailures.length} photograph(s). Review the details and retry.</p>
            )}
          </div>
          {analysisStatus !== "completed" && !["queued", "running"].includes(analysisStatus) && (
            <button className="submit" type="button" onClick={analyzeGallery} disabled={busy}>
              {["partial_failure", "failed"].includes(analysisStatus) ? "Retry analysis" : "Analyze gallery"}
            </button>
          )}
          {analysisFailures.length > 0 && (
            <ul className="analysis-failures">
              {analysisFailures.map((failure) => (
                <li key={failure.photoId}><strong>{failure.originalFilename}</strong><span>{failure.message}</span></li>
              ))}
            </ul>
          )}
        </section>
      )}
    </main>
  );
}
