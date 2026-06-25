"""HunterAI tools CLI — the setup/management entrypoint for security tools.

Usage (inside WSL / Linux)::

    python -m app.tools_cli status            # show required vs installed
    python -m app.tools_cli setup             # install all required tools
    python -m app.tools_cli setup --force     # reinstall (re-verify) everything
    python -m app.tools_cli install httpx     # install a single tool
    python -m app.tools_cli paths             # print resolved executable paths

Also exposed as the ``hunterai-tools`` console script.
"""

from __future__ import annotations

import argparse
import sys

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.infrastructure.tools import build_tool_manager
from app.infrastructure.tools.errors import ToolError

logger = get_logger("tools_cli")


def _cmd_status(manager) -> int:
    print(f"Managed tools dir: {manager.tools_dir}\n")
    rows = manager.status()
    width = max((len(r.name) for r in rows), default=4)
    for r in rows:
        mark = "✓" if r.installed and not r.needs_install else "✗"
        installed = r.installed_version or "-"
        print(
            f"  {mark} {r.name.ljust(width)}  required={r.required_version}  "
            f"installed={installed}"
        )
    missing = [r.name for r in rows if r.needs_install]
    if missing:
        print(f"\n{len(missing)} tool(s) need install: {', '.join(missing)}")
        print("Run:  python -m app.tools_cli setup")
    else:
        print("\nAll tools installed.")
    return 0


def _install_many(manager, names: list[str], *, force: bool) -> int:
    failures = 0
    for name in names:
        try:
            installed = manager.install(name, force=force)
            print(f"  ✓ {installed.name} v{installed.version}")
            print(f"      path:   {installed.path}")
            print(f"      sha256: {installed.sha256}")
        except ToolError as exc:
            failures += 1
            print(f"  ✗ {name}: {exc}", file=sys.stderr)
    if failures:
        print(f"\n{failures} tool(s) failed to install.", file=sys.stderr)
        return 1
    print("\nDone. Pin the printed sha256 values in the registry for reproducible installs.")
    return 0


def _cmd_setup(manager, *, force: bool) -> int:
    names = manager.registry.names()
    print(f"Installing {len(names)} tool(s) into {manager.tools_dir} ...\n")
    return _install_many(manager, names, force=force)


def _cmd_install(manager, names: list[str], *, force: bool) -> int:
    return _install_many(manager, names, force=force)


def _cmd_paths(manager) -> int:
    for spec in manager.registry.all():
        try:
            print(f"{spec.name}: {manager.resolve_path(spec.name)}")
        except ToolError:
            print(f"{spec.name}: (not installed)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hunterai-tools", description="HunterAI tool management")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show required vs installed tools")

    p_setup = sub.add_parser("setup", help="Install all required tools")
    p_setup.add_argument("--force", action="store_true", help="Reinstall even if present")

    p_install = sub.add_parser("install", help="Install one or more specific tools")
    p_install.add_argument("names", nargs="+", help="Tool name(s), e.g. subfinder httpx")
    p_install.add_argument("--force", action="store_true", help="Reinstall even if present")

    sub.add_parser("paths", help="Print resolved executable paths")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(debug=get_settings().debug)
    manager = build_tool_manager()

    if args.command == "status":
        return _cmd_status(manager)
    if args.command == "setup":
        return _cmd_setup(manager, force=args.force)
    if args.command == "install":
        return _cmd_install(manager, args.names, force=args.force)
    if args.command == "paths":
        return _cmd_paths(manager)
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
