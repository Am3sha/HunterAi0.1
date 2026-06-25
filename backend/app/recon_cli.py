"""HunterAI recon CLI — run the Sprint 0 pipeline end-to-end from the terminal.

Usage (inside WSL / Linux, tools installed via `python -m app.tools_cli setup`)::

    python -m app.recon_cli example.com

Authorized testing only. Prints a summary plus a sample of each result type.
This is a developer convenience; the HTTP API arrives in Milestone 4.
"""

from __future__ import annotations

import argparse
import sys

from app.application.use_cases.run_recon import RunReconUseCase
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.domain.entities.scan import Scan
from app.domain.entities.target import Target
from app.infrastructure.recon import build_recon_pipeline
from app.infrastructure.tools import build_tool_manager


def _print_summary(scan: Scan) -> None:
    print(f"\nScan {scan.id} — {scan.status.value}")
    print(f"  target:     {scan.target_domain}")
    print(f"  subdomains: {len(scan.subdomains)}")
    print(f"  services:   {len(scan.services)}")
    print(f"  endpoints:  {len(scan.endpoints)}")
    if scan.error:
        print(f"  error:      {scan.error}")

    for service in scan.services[:10]:
        code = service.status_code if service.status_code is not None else "-"
        title = f" — {service.title}" if service.title else ""
        print(f"    [{code}] {service.url}{title}")
    if len(scan.services) > 10:
        print(f"    ... and {len(scan.services) - 10} more services")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hunterai-recon", description="Run the recon pipeline")
    parser.add_argument("domain", help="Root domain to scan, e.g. example.com")
    args = parser.parse_args(argv)

    configure_logging(debug=get_settings().debug)

    try:
        target = Target.create(args.domain)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    tools = build_tool_manager()
    enumerator, prober, crawler = build_recon_pipeline(tools)
    use_case = RunReconUseCase(enumerator, prober, crawler)

    scan = use_case.execute(target)
    _print_summary(scan)
    return 0 if scan.status.value == "completed" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
