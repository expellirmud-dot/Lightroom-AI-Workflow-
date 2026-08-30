"""Lightroom-facing confirmation CLI for iterative Catalog Exposure2012 applies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lr_ai_exposure.config import load_config
from lr_ai_exposure.session_lifecycle import confirm_session_apply


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lr-ai-exposure-catalog-confirm")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--pass-number", type=int, required=True)
    parser.add_argument("--apply-result", type=Path, required=True)
    parser.add_argument("--bridge-result", type=Path, required=True)
    args = parser.parse_args(argv)

    root = Path.cwd()
    settings = load_config(root)
    runtime_dir = Path(settings["runtime_directory"])
    if not runtime_dir.is_absolute():
        runtime_dir = root / runtime_dir

    try:
        result = confirm_session_apply(
            runtime_directory=runtime_dir,
            session_id=args.session_id,
            pass_number=args.pass_number,
            apply_result_path=args.apply_result,
        )
        payload = {"protocol_version": "1.1", "status": "ok", **result}
        exit_code = 0
    except Exception as exc:
        payload = {
            "protocol_version": "1.1",
            "status": "error",
            "session_id": args.session_id,
            "pass_number": args.pass_number,
            "error": str(exc),
        }
        exit_code = 1

    args.bridge_result.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.bridge_result.with_suffix(args.bridge_result.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(args.bridge_result)
    print(json.dumps(payload, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
