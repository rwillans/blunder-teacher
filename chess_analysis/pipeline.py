from __future__ import annotations

import logging
from dataclasses import dataclass

from .engine_check import EngineCheckResult, run_stockfish_smoke_test
from .io_utils import discover_pgn_files, ensure_output_dir
from .pgn_parser import GameRecord, parse_pgn_files
from .reporting import write_games_summary_csv, write_summary_report_md


@dataclass
class PipelineResult:
    records: list[GameRecord]
    engine_result: EngineCheckResult
    csv_path: str
    report_path: str


def run_pipeline(input_path: str, output_path: str, player: str | None = None) -> PipelineResult:
    pgn_files = discover_pgn_files(input_path)
    output_dir = ensure_output_dir(output_path)

    records = parse_pgn_files(pgn_files, player=player)
    engine_result = run_stockfish_smoke_test()

    csv_path = str(write_games_summary_csv(output_dir, records))
    report_path = str(write_summary_report_md(output_dir, records, engine_result))

    logging.info("Wrote games summary CSV: %s", csv_path)
    logging.info("Wrote summary report: %s", report_path)

    return PipelineResult(
        records=records,
        engine_result=engine_result,
        csv_path=csv_path,
        report_path=report_path,
    )
