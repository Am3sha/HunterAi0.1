"""HunterAI scanner CLI — inspect the plugin-based scanner engine.

    python -m app.scanner_cli list     # list discovered plugins

Milestone 1 ships no real plugins, so this lists nothing until plugins are added
under app/infrastructure/scanner/plugins/. The engine wiring into the scan flow
and API arrives in later milestones.
"""

from __future__ import annotations

import argparse

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.infrastructure.scanner import build_default_registry


def _cmd_list() -> int:
    registry = build_default_registry()
    names = registry.names()
    if not names:
        print("No scanner plugins registered yet.")
        print("Add one under app/infrastructure/scanner/plugins/ (see docs/SCANNER.md).")
        return 0
    print(f"{len(names)} plugin(s):\n")
    for plugin in registry.all():
        meta = plugin.metadata
        state = "enabled" if meta.default_enabled else "disabled"
        print(f"  {meta.name:24} [{meta.category.value}] v{meta.version} ({state})")
        if meta.title:
            print(f"      {meta.title}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hunterai-scanner", description="Scanner engine tools")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="List discovered scanner plugins")
    args = parser.parse_args(argv)

    configure_logging(debug=get_settings().debug)
    if args.command == "list":
        return _cmd_list()
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
