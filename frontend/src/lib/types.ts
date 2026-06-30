/**
 * Types mirroring the backend API (see backend `app/interfaces/api/schemas`).
 * Keep in sync with the FastAPI response models.
 */

export type ScanStatus = "pending" | "running" | "completed" | "failed";

export interface Subdomain {
  host: string;
  source: string | null;
}

export interface HttpService {
  url: string;
  input: string | null;
  status_code: number | null;
  title: string | null;
  webserver: string | null;
  content_length: number | null;
  host: string | null;
  technologies: string[];
}

export interface Endpoint {
  url: string;
  method: string | null;
  source: string | null;
}

export interface Finding {
  id: string;
  plugin: string;
  name: string;
  severity: string;
  target: string;
  description: string;
  confidence: string;
  evidence: string | null;
  references: string[];
  metadata: Record<string, string>;
  // Sprint 2 M2
  cvss_version: string | null;
  cvss_vector: string | null;
  cvss_base_score: number | null;
  cwe_ids: string[];
  owasp_categories: string[];
  remediation: string | null;
}

export interface ScanCounts {
  subdomains: number;
  services: number;
  endpoints: number;
  findings: number;
}

/** Response of POST /scans. */
export interface ScanCreated {
  scan_id: string;
  status: ScanStatus;
  target_domain: string;
  created_at: string;
}

/** Response of GET /scans/{id}. */
export interface ScanDetail {
  scan_id: string;
  target_domain: string;
  status: ScanStatus;
  counts: ScanCounts;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
  subdomains: Subdomain[];
  services: HttpService[];
  endpoints: Endpoint[];
  findings: Finding[];
}

export const TERMINAL_STATUSES: ScanStatus[] = ["completed", "failed"];

export function isTerminal(status: ScanStatus): boolean {
  return TERMINAL_STATUSES.includes(status);
}
