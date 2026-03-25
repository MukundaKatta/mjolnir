"""Command-line interface for Mjolnir.

Provides quick access to dashboard snapshots and agent summaries
without writing code.
"""

from __future__ import annotations

import argparse
import json
import sys

from mjolnir import __version__
from mjolnir.config import MjolnirConfig
from mjolnir.core import DashboardEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mjolnir",
        description="Mjolnir -- real-time dashboard for AI coding agents",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show engine status")
    sub.add_parser("config", help="Print current configuration")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "status":
        engine = DashboardEngine()
        snap = engine.snapshot()
        print(json.dumps(snap, indent=2))
        return 0

    if args.command == "config":
        cfg = MjolnirConfig()
        print(json.dumps(cfg.to_dict(), indent=2))
        return 0

    parser.print_help()
    return 0
