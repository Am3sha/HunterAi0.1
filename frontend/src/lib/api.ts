/**
 * Typed HTTP client for the HunterAI backend.
 * The single place that knows about API URLs and response shapes.
 */
import type { ScanCreated, ScanDetail } from "@/lib/types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000";
const V1 = `${API_BASE}/api/v1`;

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") return data.detail;
    if (Array.isArray(data?.detail) && data.detail[0]?.msg) return data.detail[0].msg;
  } catch {
    /* ignore non-JSON bodies */
  }
  return `Request failed (${res.status})`;
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
      cache: "no-store",
    });
  } catch {
    throw new ApiError("Cannot reach the API. Is the backend running?", 0);
  }
  if (!res.ok) {
    throw new ApiError(await parseError(res), res.status);
  }
  return (await res.json()) as T;
}

/** Start a new scan for a domain. */
export function createScan(domain: string): Promise<ScanCreated> {
  return request<ScanCreated>(`${V1}/scans`, {
    method: "POST",
    body: JSON.stringify({ domain }),
  });
}

/** Fetch a scan's current status and results. */
export function getScan(scanId: string): Promise<ScanDetail> {
  return request<ScanDetail>(`${V1}/scans/${scanId}`);
}
