import { ResultsCard } from "@/components/scan/results-card";
import {
  EndpointsTable,
  FindingsTable,
  ServicesTable,
  SubdomainsTable,
} from "@/components/scan/result-tables";
import type { ScanDetail } from "@/lib/types";

/** Renders scan results, findings first. */
export function ScanResults({ scan }: { scan: ScanDetail }) {
  return (
    <div className="space-y-4">
      <ResultsCard
        title="Findings"
        count={scan.findings.length}
        emptyText="No findings yet."
      >
        <FindingsTable rows={scan.findings} />
      </ResultsCard>

      <ResultsCard
        title="Live HTTP services"
        count={scan.services.length}
        emptyText="No live services found yet."
      >
        <ServicesTable rows={scan.services} />
      </ResultsCard>

      <ResultsCard
        title="Subdomains"
        count={scan.subdomains.length}
        emptyText="No subdomains found yet."
      >
        <SubdomainsTable rows={scan.subdomains} />
      </ResultsCard>

      <ResultsCard
        title="Endpoints"
        count={scan.endpoints.length}
        emptyText="No endpoints found yet."
      >
        <EndpointsTable rows={scan.endpoints} />
      </ResultsCard>
    </div>
  );
}
