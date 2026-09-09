import {
  OPTIMIZATIONS_URL,
  OPTIMIZE_URL,
  RESUME_TEXT_URL,
  RESUME_UPLOAD_URL,
  RESUME_URL,
} from "./constants";
import type {
  OptimizationDetail,
  OptimizationSummary,
  OptimizeRequest,
  OptimizeResult,
  ResumeStatus,
} from "../types";

async function parseError(res: Response): Promise<string> {
  let detail = `Request failed (${res.status})`;
  try {
    const body = await res.json();
    if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
  } catch {
    /* keep default */
  }
  return detail;
}

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<T>;
}

// --- Resume ---
export function getResumeStatus(): Promise<ResumeStatus> {
  return fetch(RESUME_URL).then((r) => jsonOrThrow<ResumeStatus>(r));
}

export function setResumeText(resume: string): Promise<ResumeStatus> {
  return fetch(RESUME_TEXT_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resume }),
  }).then((r) => jsonOrThrow<ResumeStatus>(r));
}

export function uploadResume(file: File): Promise<ResumeStatus> {
  const form = new FormData();
  form.append("file", file);
  return fetch(RESUME_UPLOAD_URL, { method: "POST", body: form }).then((r) =>
    jsonOrThrow<ResumeStatus>(r)
  );
}

export function clearResume(): Promise<ResumeStatus> {
  return fetch(RESUME_URL, { method: "DELETE" }).then((r) =>
    jsonOrThrow<ResumeStatus>(r)
  );
}

// --- Optimizer ---
export function runOptimize(
  payload: OptimizeRequest,
  signal?: AbortSignal
): Promise<OptimizeResult> {
  return fetch(OPTIMIZE_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  }).then((r) => jsonOrThrow<OptimizeResult>(r));
}

export function listOptimizations(): Promise<OptimizationSummary[]> {
  return fetch(OPTIMIZATIONS_URL).then((r) =>
    jsonOrThrow<OptimizationSummary[]>(r)
  );
}

export function getOptimization(id: number): Promise<OptimizationDetail> {
  return fetch(`${OPTIMIZATIONS_URL}/${id}`).then((r) =>
    jsonOrThrow<OptimizationDetail>(r)
  );
}

export async function deleteOptimization(id: number): Promise<void> {
  const res = await fetch(`${OPTIMIZATIONS_URL}/${id}`, { method: "DELETE" });
  if (!res.ok && res.status !== 204) throw new Error(await parseError(res));
}
