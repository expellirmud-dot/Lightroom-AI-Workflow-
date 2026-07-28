"""One-shot CLI for Lightroom AI Exposure Assist MVP scaffold."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lr_ai_exposure.config import load_config, ConfigError


def main(argv: list[str] | None = None) -> int:
    """Entry point for the lr-ai-exposure CLI."""
    parser = argparse.ArgumentParser(
        prog="lr-ai-exposure",
        description="Lightroom AI Exposure Assist (MVP scaffold)",
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Validate configuration and print a summary",
    )
    args = parser.parse_args(argv)

    if not args.check_config:
        parser.print_help()
        return 0

    root = Path.cwd()
    try:
        settings = load_config(root)
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    summary = {
        "status": "ok",
        "dry_run": settings["dry_run"],
        "maximum_delta_ev": settings["maximum_delta_ev"],
        "minimum_apply_confidence": settings["minimum_apply_confidence"],
        "preview_size": settings["preview_size"],
        "runtime_directory": settings["runtime_directory"],
    }

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
