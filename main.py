from __future__ import annotations

import argparse
import logging
import sys

from chess_analysis import run_pipeline
from chess_analysis.io_utils import InputPathError

DEFAULT_INPUT_DIR = "inputs"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local chess PGN analysis tool (v5)")
    parser.add_argument(
        "--input",
        required=False,
        default=None,
        help="Optional path to a PGN file or folder of PGN files (defaults to ./inputs)",
    )
    parser.add_argument("--output", required=True, help="Output directory for generated reports")
    parser.add_argument(
        "--player",
        required=False,
        default=None,
        help="Optional player name filter (matches White or Black exactly, case-insensitive)",
    )
    parser.add_argument(
        "--player-mistakes-only",
        action="store_true",
        help="When used with --player, keep only critical moments where that player was side to move",
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

    input_path = args.input or DEFAULT_INPUT_DIR

    logging.info("Starting chess analysis pipeline")
    logging.info("Input path: %s", input_path)
    if args.player:
        logging.info("Applying player filter: %s", args.player)
    if args.player_mistakes_only and not args.player:
        logging.warning("--player-mistakes-only ignored because --player was not provided")
    logging.info("Engine depth: %d | Eval threshold: %d cp", args.engine_depth, args.eval_threshold)

    try:
        result = run_pipeline(
            input_path,
            args.output,
            player=args.player,
            player_mistakes_only=args.player_mistakes_only,
            engine_depth=args.engine_depth,
            eval_threshold=args.eval_threshold,
        )
    except InputPathError as exc:
        if args.input is None:
            logging.error(
                "Input error: %s (default input directory is ./%s)",
                exc,
                DEFAULT_INPUT_DIR,
            )
        else:
            logging.error("Input error: %s", exc)
        return 2
    except Exception as exc:
        logging.exception("Unexpected error: %s", exc)
        return 1

    logging.info("Analyzed %d PGN file(s)", result.pgn_file_count)
    logging.info("Processed %d games", len(result.records))
    logging.info("Detected %d critical moments", len(result.critical_positions))
    logging.info("Exported %d puzzles", len(result.puzzles))
    logging.info("Primary app data written to: %s", result.puzzles_json_path)
    if result.web_puzzles_json_path:
        logging.info("React viewer data synced to: %s", result.web_puzzles_json_path)
    logging.info("Stockfish smoke test success: %s", result.engine_result.success)

    if not result.engine_result.success:
        logging.warning("Stockfish smoke test failed: %s", result.engine_result.detail)

    return 0


if __name__ == "__main__":
    sys.exit(main())
