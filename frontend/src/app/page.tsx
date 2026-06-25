"use client";

import { ScanForm } from "@/components/scan/scan-form";
import { ScanResults } from "@/components/scan/scan-results";
import { ScanStatusPanel } from "@/components/scan/scan-status";
import { useScan } from "@/hooks/use-scan";

export default function HomePage() {
  const { scan, error, isBusy, start, reset } = useScan();

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <header className="mb-8 space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">HunterAI</h1>
        <p className="text-sm text-muted-foreground">
          Reconnaissance MVP — authorized testing only.
        </p>
      </header>

      <section className="space-y-6">
        <ScanForm
          onStart={start}
          onReset={reset}
          isBusy={isBusy}
          hasScan={scan !== null || error !== null}
        />

        {error && !scan && (
          <p className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </p>
        )}

        {scan && (
          <div className="space-y-6">
            <ScanStatusPanel scan={scan} />
            <ScanResults scan={scan} />
          </div>
        )}
      </section>
    </main>
  );
}
