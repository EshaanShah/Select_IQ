import { ChangeEvent, useEffect, useRef, useState } from "react";

import {
  ApiError,
  createProject,
  getComparisonProgress,
  getProjectStatus,
  savePromptAndTarget,
  startAnalysis,
  uploadPhotos,
} from "../shared/api/client";
import { InterpretationPanel } from "../features/creative-brief/InterpretationPanel";
import { ComparisonPage } from "../features/comparisons/ComparisonPage";
import { GuidedSteps, type ComparisonProgress } from "../features/evaluation/GuidedSteps";
import { ProposalPanel } from "../features/gallery-review/ProposalPanel";
import type {
  AnalysisFailure,
  AnalysisStatus,
  ImportFailure,
  ProjectStatus,
  Proposal,
} from "../shared/types";
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
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus>("idle");
  const [analysisCompleted, setAnalysisCompleted] = useState(0);
  const [analysisFailures, setAnalysisFailures] = useState<AnalysisFailure[]>([]);
  const [analysisModel, setAnalysisModel] = useState<string | null>(null);
  const [comparisonsStarted, setComparisonsStarted] = useState(false);
  const [comparisonProgress, setComparisonProgress] = useState<ComparisonProgress | null>(null);
  const [proposal, setProposal] = useState<Proposal | null>(null);

  function applyStatus(status: ProjectStatus) {
    setAcceptedCount(status.acceptedCount);
    setFailures(status.failures);
    setPrompt(status.prompt ?? "");
    setTarget(status.target?.toString() ?? "");
    setBriefSaved(Boolean(status.prompt && status.target));
    setAnalysisStatus((current) =>
      status.analysisStatus === "idle" && current === "queued"
        ? current
        : (status.analysisStatus ?? "idle"),
    );
    setAnalysisCompleted(status.analysisCompleted ?? 0);
    setAnalysisFailures(status.analysisFailures ?? []);
    setAnalysisModel(status.analysisModel ?? null);
  }

  useEffect(() => {
    folderInput.current?.setAttribute("webkitdirectory", "");
  }, []);

  useEffect(() => {
    if (!projectId || analysisStatus !== "completed" || comparisonsStarted) return;
    let cancelled = false;
    getComparisonProgress(projectId)
      .then((progress) => {
        if (!cancelled) setComparisonProgress(progress);
      })
      .catch(() => {
        // Progress is advisory; the comparison step reports its own errors when opened.
      });
    return () => {
      cancelled = true;
    };
  }, [analysisStatus, comparisonsStarted, projectId]);

  useEffect(() => {
    if (!projectId || projectId !== projectToRestore.current) return;
    let cancelled = false;
    getProjectStatus(projectId)
      .then((status) => {
        if (!cancelled) {
          applyStatus(status);
        }
      })
      .catch((reason: unknown) => {
        if (cancelled) return;
        if (reason instanceof ApiError && reason.status === 404) {
          window.localStorage.removeItem(projectStorageKey);
          setProjectId(null);
        } else {
          setError(reason instanceof Error ? reason.message : "The saved project could not be loaded.");
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
          if (!cancelled) {
            setError(
              reason instanceof Error ? reason.message : "Analysis status could not be loaded.",
            );
          }
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
      setAnalysisStatus("idle");
    } catch (reason) {
      setBriefError(reason instanceof Error ? reason.message : "The brief could not be saved.");
    } finally {
      setBriefBusy(false);
    }
  }

  async function analyzeGallery() {
    if (!projectId || !briefSaved) return;
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
  const savedTarget = briefSaved && /^\d+$/.test(target) ? Number(target) : null;

  function startNewCull() {
    window.localStorage.removeItem(projectStorageKey);
    projectToRestore.current = null;
    setSelectedFiles([]);
    setProjectId(null);
    setAcceptedCount(0);
    setFailures([]);
    setBatchSummary(null);
    setBusy(false);
    setError(null);
    setPrompt("");
    setTarget("");
    setBriefBusy(false);
    setBriefError(null);
    setBriefSaved(false);
    setAnalysisStatus("idle");
    setAnalysisCompleted(0);
    setAnalysisFailures([]);
    setAnalysisModel(null);
    setComparisonsStarted(false);
    setComparisonProgress(null);
    setProposal(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <main className="shell">
      <header className="hero">
        <div className="topbar">
          <div className="brand-lockup">
            <span className="brand-mark" aria-hidden="true">S</span>
            <span>SelectIQ <small>Alpha</small></span>
          </div>
          <div className="topbar-actions">
            <span className="privacy-status"><i aria-hidden="true" />Private local workspace</span>
            <button className="new-cull" type="button" onClick={startNewCull}>
              Start new cull
            </button>
          </div>
        </div>
        <div className="hero-copy">
          <p className="eyebrow">AI-assisted photo curation</p>
          <h1>Turn a full shoot into a focused story.</h1>
          <p className="lede">
            Import your gallery, describe the moments that matter, and shape a final selection
            with transparent AI guidance and your own choices.
          </p>
          <div className="hero-notes" aria-label="Workspace details">
            <span>JPEG workflow</span>
            <span>10–30 photos recommended</span>
            <span>Originals stay untouched</span>
          </div>
        </div>
      </header>

      <GuidedSteps
        acceptedCount={acceptedCount}
        savedTarget={savedTarget}
        analysisStatus={analysisStatus}
        comparisons={comparisonProgress}
        proposal={proposal && { selected: proposal.selectedCount, target: proposal.targetCount }}
      />

      <section className="upload-card" aria-labelledby="upload-title">
        <div className="card-heading">
          <div>
            <p className="section-kicker">01 · Import</p>
            <h2 id="upload-title">Choose photographs</h2>
            <p>Start with the full story. You can add individual files or an entire folder.</p>
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
            <span aria-hidden="true">＋</span> Choose files
            <input
              aria-label="Choose files"
              type="file"
              accept=".jpg,.jpeg,image/jpeg"
              multiple
              onChange={chooseFiles}
              disabled={busy || remaining === 0}
            />
          </label>
          <label className="picker secondary">
            <span aria-hidden="true">▣</span> Choose folder
            <input
              aria-label="Choose folder"
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
          <span className="capacity-detail">
            <span>{remaining} spaces remaining</span>
            <small>JPG/JPEG · 25 MB max</small>
          </span>
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
          <details>
            <summary>
              <span className="failure-summary-copy">
                <span className="failure-icon" aria-hidden="true">!</span>
                <span>
                  <h2 id="failures-title">Files that need attention</h2>
                  <small>{failures.length} {failures.length === 1 ? "file was" : "files were"} not imported</small>
                </span>
              </span>
              <span className="disclosure-label" aria-hidden="true">View details</span>
            </summary>
            <ul>
              {failures.map((failure, index) => (
                <li key={`${failure.filename}-${failure.code}-${index}`}>
                  <strong>{failure.filename}</strong>
                  <span>{failure.message}</span>
                </li>
              ))}
            </ul>
          </details>
        </section>
      )}

      {acceptedCount > 0 && (
        <>
          <section className="ready" aria-live="polite">
            <span aria-hidden="true">✓</span>
            <div>
              <strong>Gallery upload complete.</strong>
              <p>Add more photographs or save the creative brief below.</p>
            </div>
          </section>

          <section className="brief-card" aria-labelledby="brief-title">
            <p className="section-kicker">02 · Direction</p>
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
                  setAnalysisStatus("idle");
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

          <section className="analysis-card" aria-live="polite">
            <div>
              <p className="section-kicker">03 · Analyze</p>
              <h2>AI feature analysis</h2>
              {analysisStatus === "idle" && (
                <p>
                  {briefSaved
                    ? "Generate image and prompt embeddings before continuing."
                    : "Save the creative brief before starting analysis."}
                </p>
              )}
              {["queued", "running"].includes(analysisStatus) && (
                <p>{analysisCompleted} of {acceptedCount} photographs analyzed…</p>
              )}
              {analysisStatus === "completed" && (
                <p>
                  <strong>Your gallery is ready for the next step.</strong>
                  {analysisModel ? ` ${analysisModel} completed the analysis.` : ""}
                </p>
              )}
              {["partial_failure", "failed"].includes(analysisStatus) && (
                <p className="error" role="alert">
                  Analysis failed for {analysisFailures.length} photograph(s). Review the details
                  and retry.
                </p>
              )}
            </div>
            {analysisStatus !== "completed" &&
              !["queued", "running"].includes(analysisStatus) && (
                <button
                  className="submit"
                  type="button"
                  onClick={analyzeGallery}
                  disabled={busy || !briefSaved}
                >
                  {["partial_failure", "failed"].includes(analysisStatus)
                    ? "Retry analysis"
                    : "Analyze gallery"}
                </button>
              )}
            {analysisFailures.length > 0 && (
              <ul className="analysis-failures">
                {analysisFailures.map((failure) => (
                  <li key={failure.photoId}>
                    <strong>{failure.originalFilename}</strong>
                    <span>{failure.message}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {projectId && analysisStatus === "completed" && (
            <>
              <InterpretationPanel projectId={projectId} target={Number(target) || null} />
              {!comparisonsStarted ? (
                <section className="analysis-card">
                  <p className="section-kicker">04 · Refine</p>
                  <h2>Pairwise feedback</h2>
                  <p>Choose between photographs to teach SelectIQ your preferences.</p>
                  <button
                    className="submit"
                    type="button"
                    onClick={() => setComparisonsStarted(true)}
                  >
                    Start comparisons
                  </button>
                </section>
              ) : (
                <ComparisonPage projectId={projectId} onProgress={setComparisonProgress} />
              )}
              {savedTarget !== null && (
                <ProposalPanel
                  projectId={projectId}
                  savedTarget={savedTarget}
                  onProposal={setProposal}
                />
              )}
            </>
          )}
        </>
      )}
    </main>
  );
}
