from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from .critical_analysis import CriticalPosition, extract_critical_positions
from .engine_check import DEFAULT_STOCKFISH_PATH, EngineCheckResult, run_stockfish_smoke_test
from .io_utils import discover_pgn_files, ensure_output_dir
from .pgn_parser import GameRecord, parse_pgn_files
from .puzzles import PuzzleRecord, build_puzzles
from .reporting import (
    write_critical_positions_csv,
    write_games_summary_csv,
    write_puzzle_report_html,
    write_puzzles_csv,
    write_summary_report_md,
)


def _filter_player_mistakes_only(
    critical_positions: list[CriticalPosition],
    player: str | None,
    player_mistakes_only: bool,
) -> list[CriticalPosition]:
    if not player or not player_mistakes_only:
        return critical_positions

    normalized_player = player.strip().lower()
    filtered: list[CriticalPosition] = []
    for critical in critical_positions:
        side_to_move = critical.side_to_move.strip().lower()
        if side_to_move == "white" and critical.white.strip().lower() == normalized_player:
            filtered.append(critical)
        elif side_to_move == "black" and critical.black.strip().lower() == normalized_player:
            filtered.append(critical)
    return filtered


@dataclass
class PipelineResult:
    records: list[GameRecord]
    critical_positions: list[CriticalPosition]
    puzzles: list[PuzzleRecord]
    engine_result: EngineCheckResult
    input_path: str
    player_filter: str | None
    player_mistakes_only: bool
    pgn_files: list[str]
    pgn_file_count: int
    csv_path: str
    critical_csv_path: str
    puzzles_csv_path: str
    puzzle_html_path: str
    report_path: str


def run_pipeline(
    input_path: str,
    output_path: str,
    player: str | None = None,
    player_mistakes_only: bool = False,
    engine_depth: int = 14,
    eval_threshold: int = 150,
) -> PipelineResult:
    pgn_files = discover_pgn_files(input_path)
    output_dir = ensure_output_dir(output_path)

    parsed_games = parse_pgn_files(pgn_files, player=player)
    records = [parsed.metadata for parsed in parsed_games]

    engine_result = run_stockfish_smoke_test()

    engine_path = os.environ.get("STOCKFISH_PATH", DEFAULT_STOCKFISH_PATH)
    critical_positions = extract_critical_positions(
        ((parsed.metadata, parsed.game) for parsed in parsed_games),
        engine_path=engine_path,
        engine_depth=engine_depth,
        eval_threshold=eval_threshold,
    )
    critical_positions = _filter_player_mistakes_only(
        critical_positions,
        player=player,
        player_mistakes_only=player_mistakes_only,
    )

    puzzles = build_puzzles(critical_positions)

    csv_path = str(write_games_summary_csv(output_dir, records))
    critical_csv_path = str(write_critical_positions_csv(output_dir, critical_positions))
    puzzles_csv_path = str(write_puzzles_csv(output_dir, puzzles))
    puzzle_html_path = str(
        write_puzzle_report_html(
            output_dir,
            puzzles,
            input_path=input_path,
            player_filter=player,
            player_mistakes_only=player_mistakes_only and bool(player),
        )
    )
    report_path = str(
        write_summary_report_md(
            output_dir,
            records,
            critical_positions,
            puzzles,
            engine_result,
            input_path=input_path,
            player_filter=player,
            player_mistakes_only=player_mistakes_only and bool(player),
            pgn_files=[str(p) for p in pgn_files],
        )
    )

    logging.info("Wrote games summary CSV: %s", csv_path)
    logging.info("Wrote critical positions CSV: %s", critical_csv_path)
    logging.info("Wrote puzzles CSV: %s", puzzles_csv_path)
    logging.info("Wrote puzzle HTML report: %s", puzzle_html_path)
    logging.info("Wrote summary report: %s", report_path)

    return PipelineResult(
        records=records,
        critical_positions=critical_positions,
        puzzles=puzzles,
        engine_result=engine_result,
        input_path=input_path,
        player_filter=player,
        player_mistakes_only=player_mistakes_only and bool(player),
        pgn_files=[str(p) for p in pgn_files],
        pgn_file_count=len(pgn_files),
        csv_path=csv_path,
        critical_csv_path=critical_csv_path,
        puzzles_csv_path=puzzles_csv_path,
        puzzle_html_path=puzzle_html_path,
        report_path=report_path,
    )
