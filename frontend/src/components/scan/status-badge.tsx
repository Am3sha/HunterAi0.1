import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ScanStatus } from "@/lib/types";

const STATUS_CONFIG: Record<
  ScanStatus,
  { label: string; variant: "secondary" | "success" | "destructive" | "outline"; pulse?: boolean }
> = {
  pending: { label: "Pending", variant: "outline" },
  running: { label: "Running", variant: "secondary", pulse: true },
  completed: { label: "Completed", variant: "success" },
  failed: { label: "Failed", variant: "destructive" },
};

export function ScanStatusBadge({ status }: { status: ScanStatus }) {
  const { label, variant, pulse } = STATUS_CONFIG[status];
  return (
    <Badge variant={variant} className={cn(pulse && "animate-pulse")}>
      {label}
    </Badge>
  );
}

/** Color a numeric HTTP status code by class (2xx/3xx/4xx/5xx). */
export function HttpStatusBadge({ code }: { code: number | null }) {
  if (code === null) return <span className="text-muted-foreground">—</span>;
  const variant =
    code < 300 ? "success" : code < 400 ? "secondary" : code < 500 ? "warning" : "destructive";
  return <Badge variant={variant}>{code}</Badge>;
}
