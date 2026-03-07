from __future__ import annotations

from pathlib import Path

from chess_analysis.critical_analysis import extract_critical_positions
from chess_analysis.pipeline import run_pipeline


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

    result = run_pipeline(str(pgn_path), str(out_path), engine_depth=10, eval_threshold=120)

    assert len(result.records) == 1
    assert (out_path / "games_summary.csv").exists()
    assert (out_path / "critical_positions.csv").exists()
    assert (out_path / "summary_report.md").exists()
    assert isinstance(result.critical_positions, list)


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
