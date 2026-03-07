from __future__ import annotations

import argparse
import logging
import sys

from chess_analysis import run_pipeline
from chess_analysis.io_utils import InputPathError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local chess PGN analysis tool (v1)")
    parser.add_argument("--input", required=True, help="Path to a PGN file or folder of PGN files")
    parser.add_argument("--output", required=True, help="Output directory for generated reports")
    parser.add_argument(
        "--player",
        required=False,
        default=None,
        help="Optional player name filter (matches White or Black exactly, case-insensitive)",
    )
    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = build_parser().parse_args()

    logging.info("Starting chess analysis pipeline")
    if args.player:
        logging.info("Applying player filter: %s", args.player)

    try:
        result = run_pipeline(args.input, args.output, player=args.player)
    except InputPathError as exc:
        logging.error("Input error: %s", exc)
        return 2
    except Exception as exc:
        logging.exception("Unexpected error: %s", exc)
        return 1

    logging.info("Processed %d games", len(result.records))
    logging.info("Stockfish smoke test success: %s", result.engine_result.success)

    if not result.engine_result.success:
        logging.warning("Stockfish smoke test failed: %s", result.engine_result.detail)

    return 0


if __name__ == "__main__":
    sys.exit(main())
