/**
 * Client for the optional emojibench FastAPI backend.
 *
 * The web kitchen works offline without this client. When the backend is
 * available, provider generation, review, and story export open up.
 */

export type ApiAsset = {
  id: string;
  name: string;
  category: string;
  status: string;
  kind: string;
};

export type GenerationJob = {
  id: string;
  state: "queued" | "running" | "succeeded" | "failed";
  input_ids: [string, string];
  provider: string;
  asset_id: string | null;
  error: string | null;
  asset?: ApiAsset & { image_uri?: string };
};

export type StoryPayload = {
  title: string;
  audience: string;
  panels: Array<{
    asset_id: string;
    caption: string;
    evidence_status: string;
    references?: string[];
  }>;
};

function apiBase(): string {
  const configured = import.meta.env.VITE_API_BASE;
  return typeof configured === "string" ? configured : "/api";
}

export async function checkBackend(): Promise<boolean> {
  try {
    const response = await fetch(`${apiBase()}/assets`);
    return response.ok;
  } catch {
    return false;
  }
}

export async function startGeneration(
  first: string,
  second: string,
  provider: "mock" | "openai",
): Promise<GenerationJob> {
  const response = await fetch(`${apiBase()}/generations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ first, second, provider }),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Generation request failed: ${detail}`);
  }
  return (await response.json()) as GenerationJob;
}

export async function pollJob(jobId: string): Promise<GenerationJob> {
  const response = await fetch(`${apiBase()}/generations/${jobId}`);
  if (!response.ok) {
    throw new Error(`Job lookup failed: ${jobId}`);
  }
  return (await response.json()) as GenerationJob;
}

export async function approveDraft(
  assetId: string,
  reviewer: string,
): Promise<ApiAsset> {
  const response = await fetch(`${apiBase()}/review/${assetId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reviewer }),
  });
  if (!response.ok) {
    throw new Error(`Approval failed: ${await response.text()}`);
  }
  return (await response.json()) as ApiAsset;
}

export async function rejectDraft(
  assetId: string,
  reviewer: string,
  reason: string,
): Promise<ApiAsset> {
  const response = await fetch(`${apiBase()}/review/${assetId}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reviewer, reason }),
  });
  if (!response.ok) {
    throw new Error(`Rejection failed: ${await response.text()}`);
  }
  return (await response.json()) as ApiAsset;
}

export async function exportStory(story: StoryPayload): Promise<string> {
  const response = await fetch(`${apiBase()}/stories`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(story),
  });
  if (!response.ok) {
    throw new Error(`Story export failed: ${await response.text()}`);
  }
  const body = (await response.json()) as { export: string };
  return body.export;
}

export async function waitForJob(
  jobId: string,
  intervalMs = 200,
  maxAttempts = 100,
): Promise<GenerationJob> {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const job = await pollJob(jobId);
    if (job.state === "succeeded" || job.state === "failed") {
      return job;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error("Job did not finish in time");
}
