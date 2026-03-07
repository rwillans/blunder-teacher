from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from .critical_analysis import CriticalPosition, extract_critical_positions
from .engine_check import DEFAULT_STOCKFISH_PATH, EngineCheckResult, run_stockfish_smoke_test
from .io_utils import discover_pgn_files, ensure_output_dir
from .pgn_parser import GameRecord, parse_pgn_files
from .reporting import write_critical_positions_csv, write_games_summary_csv, write_summary_report_md


@dataclass
class PipelineResult:
    records: list[GameRecord]
    critical_positions: list[CriticalPosition]
    engine_result: EngineCheckResult
    csv_path: str
    critical_csv_path: str
    report_path: str


def run_pipeline(
    input_path: str,
    output_path: str,
    player: str | None = None,
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

    csv_path = str(write_games_summary_csv(output_dir, records))
    critical_csv_path = str(write_critical_positions_csv(output_dir, critical_positions))
    report_path = str(write_summary_report_md(output_dir, records, critical_positions, engine_result))

    logging.info("Wrote games summary CSV: %s", csv_path)
    logging.info("Wrote critical positions CSV: %s", critical_csv_path)
    logging.info("Wrote summary report: %s", report_path)

    return PipelineResult(
        records=records,
        critical_positions=critical_positions,
        engine_result=engine_result,
        csv_path=csv_path,
        critical_csv_path=critical_csv_path,
        report_path=report_path,
    )
