from __future__ import annotations

import csv
from pathlib import Path

from chess_analysis.critical_analysis import CriticalPosition, extract_critical_positions
from chess_analysis.engine_check import EngineCheckResult
from chess_analysis.pipeline import run_pipeline
from chess_analysis.reporting import write_summary_report_md


SAMPLE_PGN = """[Event "Casual Game"]
[Site "Internet"]
[Date "2024.01.01"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 1-0

[Event "Training"]
[Site "Local"]
[Date "2024.01.02"]
[White "Carol"]
[Black "Alice"]
[Result "0-1"]
[ECO "C20"]
[Opening "King's Pawn Game"]

1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 0-1
"""

BLUNDER_PGN = """[Event "Blunder Demo"]
[Site "Test"]
[Date "2024.02.02"]
[White "WhitePlayer"]
[Black "BlackPlayer"]
[Result "0-1"]

1. f3 e5 2. g4 Qh4# 0-1
"""


def test_pipeline_writes_outputs_with_critical_positions(tmp_path: Path) -> None:
    pgn_path = tmp_path / "sample.pgn"
    out_path = tmp_path / "out"
    pgn_path.write_text(BLUNDER_PGN, encoding="utf-8")

    run_pipeline(str(pgn_path), str(out_path), engine_depth=10, eval_threshold=120)

    assert (out_path / "games_summary.csv").exists()
    assert (out_path / "critical_positions.csv").exists()
    assert (out_path / "summary_report.md").exists()

    with (out_path / "critical_positions.csv").open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert "mate_related" in (reader.fieldnames or [])


def test_extract_critical_positions_handles_missing_engine() -> None:
    critical = extract_critical_positions([], engine_path="/definitely/missing/stockfish")
    assert critical == []


def test_pipeline_does_not_crash_when_engine_missing_for_critical(tmp_path: Path, monkeypatch) -> None:
    pgn_path = tmp_path / "sample.pgn"
    out_path = tmp_path / "out"
    pgn_path.write_text(SAMPLE_PGN, encoding="utf-8")

    monkeypatch.setenv("STOCKFISH_PATH", "/definitely/missing/stockfish")
    result = run_pipeline(str(pgn_path), str(out_path), engine_depth=8, eval_threshold=150)

    assert len(result.records) == 2
    assert result.critical_positions == []
    assert (out_path / "critical_positions.csv").exists()


def test_summary_report_non_mate_stats_are_separate(tmp_path: Path) -> None:
    records = []
    critical = [
        CriticalPosition(
            source_file="a.pgn",
            game_index=1,
            event="E",
            site="S",
            date="2024.01.01",
            white="W",
            black="B",
            result="1-0",
            move_number=10,
            side_to_move="White",
            fen="fen",
            played_move="Qh5",
            engine_best_move="Nf3",
            eval_before=200.0,
            eval_after=0.0,
            eval_swing=200.0,
            mate_related=False,
            eco="C20",
            opening="KP",
        ),
        CriticalPosition(
            source_file="a.pgn",
            game_index=1,
            event="E",
            site="S",
            date="2024.01.01",
            white="W",
            black="B",
            result="1-0",
            move_number=20,
            side_to_move="Black",
            fen="fen2",
            played_move="g6",
            engine_best_move="Qf6",
            eval_before=100000.0,
            eval_after=-100000.0,
            eval_swing=200000.0,
            mate_related=True,
            eco="C20",
            opening="KP",
        ),
    ]
    engine_result = EngineCheckResult(success=True, engine_path="/usr/games/stockfish", detail="ok")

    report = write_summary_report_md(tmp_path, records, critical, engine_result)
    text = report.read_text(encoding="utf-8")

    assert "Number of mate-related critical moments: **1**" in text
    assert "Average centipawn swing (non-mate): **200.00 cp**" in text
    assert "Maximum centipawn swing (non-mate): **200.00 cp**" in text
