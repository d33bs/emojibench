import { useState } from "react";

import {
  approveDraft,
  rejectDraft,
  startGeneration,
  waitForJob,
  type GenerationJob,
} from "./api";

type GenerationPanelProps = {
  backendReady: boolean;
  firstId: string | null;
  secondId: string | null;
};

/**
 * Provider generation controls. Visible only with a live backend; the
 * offline page keeps its mock preview and never calls the network.
 */
export default function GenerationPanel({
  backendReady,
  firstId,
  secondId,
}: GenerationPanelProps) {
  const [provider, setProvider] = useState<"mock" | "openai">("mock");
  const [job, setJob] = useState<GenerationJob | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reviewer, setReviewer] = useState("");
  const [reason, setReason] = useState("");

  const pairReady = firstId !== null && secondId !== null;

  async function generate() {
    if (!pairReady || busy) {
      return;
    }
    setBusy(true);
    setError(null);
    setJob(null);
    try {
      const submitted = await startGeneration(firstId, secondId, provider);
      const finished = await waitForJob(submitted.id);
      setJob(finished);
    } catch (generationError) {
      setError(
        generationError instanceof Error
          ? generationError.message
          : "Generation failed.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function decide(decision: "approve" | "reject") {
    if (!job?.asset_id || busy) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (decision === "approve") {
        await approveDraft(job.asset_id, reviewer);
      } else {
        await rejectDraft(job.asset_id, reviewer, reason || "Needs rework.");
      }
      setJob(null);
      setReason("");
    } catch (reviewError) {
      setError(
        reviewError instanceof Error
          ? reviewError.message
          : "Review failed.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (!backendReady) {
    return (
      <p className="backend-note" data-testid="backend-note">
        The offline demo shows a deterministic mock preview. Start the API
        backend to use real providers, review, and stories.
      </p>
    );
  }

  return (
    <section className="generation-panel" aria-label="Provider generation">
      <div className="generation-controls">
        <label htmlFor="provider-select">Provider</label>
        <select
          id="provider-select"
          value={provider}
          onChange={(event) =>
            setProvider(event.target.value as "mock" | "openai")
          }
        >
          <option value="mock">mock (offline)</option>
          <option value="openai">openai (paid, needs a key)</option>
        </select>
        <button
          type="button"
          className="download-button"
          disabled={!pairReady || busy}
          onClick={generate}
        >
          {busy ? "Working..." : "Generate draft"}
        </button>
      </div>

      {error && (
        <p className="generation-error" role="alert">
          {error}
        </p>
      )}

      {job && (
        <div className="job-result" data-testid="job-result">
          {job.state === "succeeded" && job.asset ? (
            <>
              <p>
                Draft ready: <strong>{job.asset_id}</strong> ({job.provider}{" "}
                provider). A human must review it before publication.
              </p>
              <div className="review-controls">
                <input
                  type="text"
                  value={reviewer}
                  placeholder="Reviewer name"
                  aria-label="Reviewer name"
                  onChange={(event) => setReviewer(event.target.value)}
                />
                <button
                  type="button"
                  disabled={busy || reviewer.trim() === ""}
                  onClick={() => decide("approve")}
                >
                  Approve
                </button>
                <button
                  type="button"
                  disabled={busy || reviewer.trim() === ""}
                  onClick={() => decide("reject")}
                >
                  Reject
                </button>
                {reason === "" && (
                  <input
                    type="text"
                    placeholder="Rejection reason (for reject)"
                    aria-label="Rejection reason"
                    onChange={(event) => setReason(event.target.value)}
                  />
                )}
              </div>
            </>
          ) : (
            <p role="alert">
              Generation failed: {job.error ?? "unknown error"}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
