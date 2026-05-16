from __future__ import annotations

import argparse
import json

from app.config import RuntimeConfig, load_environment
from app.runner import run_once


def main() -> None:
    parser = argparse.ArgumentParser(description="AI invest simulator")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run", help="run one daily simulation")
    run_parser.add_argument("--mock", action="store_true", help="use deterministic mock market data")
    run_parser.add_argument("--no-ai", action="store_true", help="skip Gemini and use quant strategy only")
    run_parser.add_argument("--force", action="store_true", help="run again even if today's simulation already exists")
    args = parser.parse_args()

    load_environment()
    if args.command == "run":
        result = run_once(RuntimeConfig(use_mock_data=args.mock, allow_ai=not args.no_ai), force=args.force)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
