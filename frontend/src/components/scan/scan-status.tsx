import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ScanStatusBadge } from "@/components/scan/status-badge";
import type { ScanDetail } from "@/lib/types";

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border p-3">
      <div className="text-2xl font-semibold tabular-nums">{value}</div>
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
    </div>
  );
}

export function ScanStatusPanel({ scan }: { scan: ScanDetail }) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div className="space-y-1">
          <CardTitle className="font-mono">{scan.target_domain}</CardTitle>
          <CardDescription>Scan {scan.scan_id}</CardDescription>
        </div>
        <ScanStatusBadge status={scan.status} />
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-3 gap-3">
          <Stat label="Subdomains" value={scan.counts.subdomains} />
          <Stat label="Services" value={scan.counts.services} />
          <Stat label="Endpoints" value={scan.counts.endpoints} />
        </div>
        {scan.status === "failed" && scan.error && (
          <p className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
            {scan.error}
          </p>
        )}
        {scan.status === "running" && (
          <p className="text-sm text-muted-foreground">
            Reconnaissance in progress — results update automatically.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
