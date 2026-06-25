import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { HttpStatusBadge } from "@/components/scan/status-badge";
import type { Endpoint, Finding, HttpService, Subdomain } from "@/lib/types";

function SeverityBadge({ severity }: { severity: string }) {
  const variants: Record<string, "destructive" | "default" | "secondary" | "outline"> = {
    critical: "destructive",
    high: "destructive",
    medium: "default",
    low: "secondary",
    info: "outline",
  };
  return <Badge variant={variants[severity] ?? "outline"}>{severity}</Badge>;
}

function ExternalLink({ href }: { href: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer noopener"
      className="font-mono text-sm text-primary underline-offset-4 hover:underline"
    >
      {href}
    </a>
  );
}

export function SubdomainsTable({ rows }: { rows: Subdomain[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Host</TableHead>
          <TableHead className="w-32">Source</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.host}>
            <TableCell className="font-mono">{row.host}</TableCell>
            <TableCell className="text-muted-foreground">{row.source ?? "—"}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function ServicesTable({ rows }: { rows: HttpService[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-20">Status</TableHead>
          <TableHead>URL</TableHead>
          <TableHead>Title</TableHead>
          <TableHead className="w-40">Tech</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.url}>
            <TableCell>
              <HttpStatusBadge code={row.status_code} />
            </TableCell>
            <TableCell>
              <ExternalLink href={row.url} />
            </TableCell>
            <TableCell className="max-w-[18rem] truncate text-muted-foreground">
              {row.title ?? "—"}
            </TableCell>
            <TableCell>
              <div className="flex flex-wrap gap-1">
                {row.technologies.length === 0
                  ? "—"
                  : row.technologies.map((tech) => (
                      <Badge key={tech} variant="outline" className="font-normal">
                        {tech}
                      </Badge>
                    ))}
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function EndpointsTable({ rows }: { rows: Endpoint[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-20">Method</TableHead>
          <TableHead>URL</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row, index) => (
          <TableRow key={`${row.method ?? "GET"}-${row.url}-${index}`}>
            <TableCell className="font-mono text-xs text-muted-foreground">
              {row.method ?? "GET"}
            </TableCell>
            <TableCell>
              <ExternalLink href={row.url} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function FindingsTable({ rows }: { rows: Finding[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-24">Severity</TableHead>
          <TableHead>Finding</TableHead>
          <TableHead>Target</TableHead>
          <TableHead className="w-32">Plugin</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.id}>
            <TableCell>
              <SeverityBadge severity={row.severity} />
            </TableCell>
            <TableCell>
              <div className="font-medium">{row.name}</div>
              {row.description && (
                <p className="text-sm text-muted-foreground">{row.description}</p>
              )}
            </TableCell>
            <TableCell>
              <ExternalLink href={row.target} />
            </TableCell>
            <TableCell className="text-sm text-muted-foreground">{row.plugin}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
