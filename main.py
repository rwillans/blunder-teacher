from __future__ import annotations

import argparse
import logging
import sys

from chess_analysis import run_pipeline
from chess_analysis.io_utils import InputPathError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local chess PGN analysis tool (v2)")
    parser.add_argument("--input", required=True, help="Path to a PGN file or folder of PGN files")
    parser.add_argument("--output", required=True, help="Output directory for generated reports")
    parser.add_argument(
        "--player",
        required=False,
        default=None,
        help="Optional player name filter (matches White or Black exactly, case-insensitive)",
    )
    parser.add_argument(
        "--engine-depth",
        type=int,
        default=14,
        help="Engine search depth for move-by-move analysis (default: 14)",
    )
    parser.add_argument(
        "--eval-threshold",
        type=int,
        default=150,
        help="Critical moment threshold in centipawns (default: 150)",
    )
    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = build_parser().parse_args()

    if args.engine_depth < 1:
        logging.error("--engine-depth must be >= 1")
        return 2
    if args.eval_threshold < 1:
        logging.error("--eval-threshold must be >= 1")
        return 2

    logging.info("Starting chess analysis pipeline")
    if args.player:
        logging.info("Applying player filter: %s", args.player)
    logging.info("Engine depth: %d | Eval threshold: %d cp", args.engine_depth, args.eval_threshold)

    try:
        result = run_pipeline(
            args.input,
            args.output,
            player=args.player,
            engine_depth=args.engine_depth,
            eval_threshold=args.eval_threshold,
        )
    except InputPathError as exc:
        logging.error("Input error: %s", exc)
        return 2
    except Exception as exc:
        logging.exception("Unexpected error: %s", exc)
        return 1

    logging.info("Processed %d games", len(result.records))
    logging.info("Detected %d critical moments", len(result.critical_positions))
    logging.info("Stockfish smoke test success: %s", result.engine_result.success)

    if not result.engine_result.success:
        logging.warning("Stockfish smoke test failed: %s", result.engine_result.detail)

    return 0


if __name__ == "__main__":
    sys.exit(main())
