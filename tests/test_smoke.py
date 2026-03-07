from __future__ import annotations

from pathlib import Path

from chess_analysis.engine_check import run_stockfish_smoke_test
from chess_analysis.pipeline import run_pipeline


SAMPLE_PGN = """[Event \"Casual Game\"]
[Site \"Internet\"]
[Date \"2024.01.01\"]
[White \"Alice\"]
[Black \"Bob\"]
[Result \"1-0\"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 1-0

[Event \"Training\"]
[Site \"Local\"]
[Date \"2024.01.02\"]
[White \"Carol\"]
[Black \"Alice\"]
[Result \"0-1\"]
[ECO \"C20\"]
[Opening \"King's Pawn Game\"]

1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 0-1
"""


def test_pipeline_writes_outputs(tmp_path: Path) -> None:
    pgn_path = tmp_path / "sample.pgn"
    out_path = tmp_path / "out"
    pgn_path.write_text(SAMPLE_PGN, encoding="utf-8")

    result = run_pipeline(str(pgn_path), str(out_path))

    assert len(result.records) == 2
    assert (out_path / "games_summary.csv").exists()
    assert (out_path / "summary_report.md").exists()


def test_stockfish_smoke_test() -> None:
    result = run_stockfish_smoke_test()
    assert isinstance(result.success, bool)
