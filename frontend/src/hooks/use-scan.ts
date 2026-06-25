"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, createScan, getScan } from "@/lib/api";
import type { ScanDetail } from "@/lib/types";

const POLL_INTERVAL_MS = 2000;

/** UI phase of the scan workflow. */
export type ScanPhase = "idle" | "starting" | "running" | "completed" | "failed";

export interface UseScanResult {
  phase: ScanPhase;
  scan: ScanDetail | null;
  error: string | null;
  isBusy: boolean;
  start: (domain: string) => Promise<void>;
  reset: () => void;
}

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return err.message;
  return "Unexpected error";
}

/**
 * Manages the create -> poll -> terminal lifecycle of a single scan.
 * Polling stops automatically on a terminal status or unmount.
 */
export function useScan(): UseScanResult {
  const [scanId, setScanId] = useState<string | null>(null);
  const [scan, setScan] = useState<ScanDetail | null>(null);
  const [phase, setPhase] = useState<ScanPhase>("idle");
  const [error, setError] = useState<string | null>(null);

  // Track the active scan id to ignore stale responses after reset/restart.
  const activeId = useRef<string | null>(null);

  const start = useCallback(async (domain: string) => {
    setError(null);
    setScan(null);
    setPhase("starting");
    try {
      const created = await createScan(domain);
      activeId.current = created.scan_id;
      setScanId(created.scan_id);
      setPhase("running");
    } catch (err) {
      setPhase("idle");
      setError(errorMessage(err));
    }
  }, []);

  const reset = useCallback(() => {
    activeId.current = null;
    setScanId(null);
    setScan(null);
    setPhase("idle");
    setError(null);
  }, []);

  useEffect(() => {
    if (!scanId || phase !== "running") return;

    let cancelled = false;
    const tick = async () => {
      try {
        const detail = await getScan(scanId);
        if (cancelled || activeId.current !== scanId) return;
        setScan(detail);
        if (detail.status === "completed" || detail.status === "failed") {
          setPhase(detail.status);
        }
      } catch (err) {
        if (cancelled) return;
        setError(errorMessage(err));
        setPhase("failed");
      }
    };

    void tick(); // immediate first poll
    const handle = setInterval(tick, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(handle);
    };
  }, [scanId, phase]);

  return {
    phase,
    scan,
    error,
    isBusy: phase === "starting" || phase === "running",
    start,
    reset,
  };
}
