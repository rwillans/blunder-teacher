from __future__ import annotations

import csv
import sys
from pathlib import Path

from chess_analysis.critical_analysis import CriticalPosition, LegalMoveOption, extract_critical_positions
from chess_analysis.engine_check import EngineCheckResult
from chess_analysis.pipeline import _filter_player_mistakes_only, run_pipeline
from chess_analysis.puzzles import assign_prompt_type, build_puzzles
from chess_analysis.reporting import write_puzzle_report_html, write_summary_report_md
from main import main


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


def _critical(
    eval_before: float,
    eval_after: float,
    mate_related: bool,
    white: str = "W",
    black: str = "B",
    side_to_move: str = "White",
) -> CriticalPosition:
    return CriticalPosition(
        source_file="a.pgn",
        game_index=1,
        event="E",
        site="S",
        date="2024.01.01",
        white=white,
        black=black,
        result="1-0",
        move_number=10,
        side_to_move=side_to_move,
        fen="fen",
        played_move="Qh5",
        engine_best_move="Nf3",
        eval_before=eval_before,
        eval_after=eval_after,
        eval_swing=eval_before - eval_after,
        mate_related=mate_related,
        eco="C20",
        opening="KP",
        played_move_uci="d1h5",
        engine_best_move_uci="g1f3",
        best_eval_display=f"{eval_before / 100:+.2f}",
        played_eval_display=f"{eval_after / 100:+.2f}",
        eval_loss_display=f"{int(eval_before - eval_after)} cp",
        best_pv_san="Nf3 Nc6",
        legal_move_options=[
            LegalMoveOption(
                uci="g1f3",
                san="Nf3",
                resulting_fen="fen-after-best",
                eval_cp=eval_before,
                eval_display=f"{eval_before / 100:+.2f}",
                eval_loss_cp=0.0,
                eval_loss_display="0 cp",
                grade="Excellent",
            ),
            LegalMoveOption(
                uci="d1h5",
                san="Qh5",
                resulting_fen="fen-after-played",
                eval_cp=eval_after,
                eval_display=f"{eval_after / 100:+.2f}",
                eval_loss_cp=eval_before - eval_after,
                eval_loss_display=f"{int(eval_before - eval_after)} cp",
                grade="Blunder" if eval_before - eval_after > 250 else "Mistake",
            ),
        ],
    )


def test_pipeline_writes_outputs_with_critical_positions_and_puzzles(tmp_path: Path) -> None:
    pgn_path = tmp_path / "sample.pgn"
    out_path = tmp_path / "out"
    pgn_path.write_text(BLUNDER_PGN, encoding="utf-8")

    run_pipeline(str(pgn_path), str(out_path), engine_depth=10, eval_threshold=120)

    assert (out_path / "games_summary.csv").exists()
    assert (out_path / "critical_positions.csv").exists()
    assert (out_path / "summary_report.md").exists()
    assert (out_path / "puzzles.csv").exists()
    assert (out_path / "puzzles.html").exists()

    with (out_path / "critical_positions.csv").open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert "mate_related" in (reader.fieldnames or [])

    with (out_path / "puzzles.csv").open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        assert "prompt_type" in fieldnames
        assert "recommended_focus" in fieldnames
        assert "legal_move_options_json" in fieldnames
        assert "best_move_uci" in fieldnames


def test_default_inputs_directory_when_input_omitted(tmp_path: Path, monkeypatch) -> None:
    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir()
    (inputs_dir / "one.pgn").write_text(SAMPLE_PGN, encoding="utf-8")

    out_dir = tmp_path / "out"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["main.py", "--output", str(out_dir), "--engine-depth", "8"])

    code = main()
    assert code == 0
    assert (out_dir / "games_summary.csv").exists()


def test_multiple_pgns_combined_and_player_filtering(tmp_path: Path) -> None:
    pgn_dir = tmp_path / "pgns"
    pgn_dir.mkdir()
    (pgn_dir / "a.pgn").write_text(
        """[Event "G1"]\n[Site "S"]\n[Date "2024.01.01"]\n[White "Rob Willans"]\n[Black "Bob"]\n[Result "1-0"]\n\n1. e4 e5 1-0\n""",
        encoding="utf-8",
    )
    (pgn_dir / "b.pgn").write_text(
        """[Event "G2"]\n[Site "S"]\n[Date "2024.01.02"]\n[White "Alice"]\n[Black "Carol"]\n[Result "0-1"]\n\n1. d4 d5 0-1\n""",
        encoding="utf-8",
    )

    out_dir = tmp_path / "out"
    result = run_pipeline(str(pgn_dir), str(out_dir), player="rob willans", engine_depth=8, eval_threshold=150)

    assert result.pgn_file_count == 2
    assert len(result.records) == 1
    assert result.records[0].white == "Rob Willans"


def test_player_mistakes_filter_helper() -> None:
    critical_positions = [
        _critical(150, 0, False, white="Rob Willans", black="Other", side_to_move="White"),
        _critical(150, 0, False, white="Rob Willans", black="Other", side_to_move="Black"),
    ]

    no_filter = _filter_player_mistakes_only(critical_positions, player="Rob Willans", player_mistakes_only=False)
    assert len(no_filter) == 2

    filtered = _filter_player_mistakes_only(critical_positions, player="rob willans", player_mistakes_only=True)
    assert len(filtered) == 1
    assert filtered[0].side_to_move == "White"


def test_player_mistakes_filter_propagates_to_csv_and_puzzles(tmp_path: Path, monkeypatch) -> None:
    pgn_path = tmp_path / "game.pgn"
    pgn_path.write_text(
        """[Event "G1"]\n[Site "S"]\n[Date "2024.01.01"]\n[White "Rob Willans"]\n[Black "Other"]\n[Result "1-0"]\n\n1. e4 e5 1-0\n""",
        encoding="utf-8",
    )
    out_path = tmp_path / "out"

    stub_critical = [
        _critical(150, -10, False, white="Rob Willans", black="Other", side_to_move="White"),
        _critical(170, -20, False, white="Rob Willans", black="Other", side_to_move="Black"),
    ]

    monkeypatch.setattr("chess_analysis.pipeline.extract_critical_positions", lambda *args, **kwargs: stub_critical)

    result = run_pipeline(
        str(pgn_path),
        str(out_path),
        player="Rob Willans",
        player_mistakes_only=True,
        engine_depth=8,
        eval_threshold=150,
    )

    assert len(result.critical_positions) == 1
    assert len(result.puzzles) == 1

    with (out_path / "critical_positions.csv").open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    with (out_path / "puzzles.csv").open("r", encoding="utf-8") as handle:
        puzzle_rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    assert len(puzzle_rows) == 1
    assert rows[0]["side_to_move"] == "White"


def test_prompt_assignment_logic() -> None:
    assert assign_prompt_type(_critical(80, -100, False)) == "Spot the danger"
    assert assign_prompt_type(_critical(-120, -150, False)) == "Defend accurately"
    assert assign_prompt_type(_critical(50, 0, False)) == "Find the best move"
    assert assign_prompt_type(_critical(100, -100000, True)) == "Spot the danger"


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
    assert result.puzzles == []
    assert (out_path / "critical_positions.csv").exists()
    assert (out_path / "puzzles.csv").exists()


def test_summary_report_non_mate_stats_and_puzzle_counts(tmp_path: Path) -> None:
    records = []
    critical = [
        _critical(200.0, 0.0, False),
        _critical(100000.0, -100000.0, True),
    ]
    puzzles = build_puzzles(critical)
    engine_result = EngineCheckResult(success=True, engine_path="/usr/games/stockfish", detail="ok")

    report = write_summary_report_md(
        tmp_path,
        records,
        critical,
        puzzles,
        engine_result,
        input_path="inputs",
        player_filter="Rob Willans",
        player_mistakes_only=True,
        pgn_files=["a.pgn", "b.pgn"],
    )
    text = report.read_text(encoding="utf-8")

    assert "Player filtering applied: **Yes**" in text
    assert "Player-mistakes-only filtering applied: **Yes**" in text
    assert "Number of PGN files analysed: **2**" in text
    assert "Total number of games processed (after filtering): **0**" in text
    assert "Number of mate-related critical moments: **1**" in text
    assert "Average centipawn swing (non-mate): **200.00 cp**" in text
    assert "Maximum centipawn swing (non-mate): **200.00 cp**" in text
    assert "Number of puzzles exported: **2**" in text
    assert "Number of mate-related puzzles: **1**" in text
    assert "Find the best move: 1" in text
    assert "Spot the danger: 1" in text


def test_puzzle_report_html_uses_single_position_viewer_with_filters_and_navigation(tmp_path: Path) -> None:
    puzzles = build_puzzles(
        [
            _critical(150.0, 0.0, False, white="Rob Willans", black="Other", side_to_move="White"),
            _critical(-120.0, -250.0, False, white="Other", black="Rob Willans", side_to_move="Black"),
        ]
    )

    html_report = write_puzzle_report_html(
        tmp_path,
        puzzles,
        input_path="inputs",
        player_filter="Rob Willans",
        player_mistakes_only=True,
    )
    text = html_report.read_text(encoding="utf-8")

    assert "Blunder Teacher v5 Training Viewer" in text
    assert 'id="prompt-filter"' in text
    assert 'id="opening-filter"' in text
    assert 'id="side-filter"' in text
    assert "Apply Filters" in text
    assert "Clear Filters" in text
    assert "Puzzle 0 of 0" in text
    assert "Submit Move" in text
    assert "Reveal Answer" in text
    assert "No puzzles match the current filters" in text
    assert "Open on Lichess" in text
    assert '"legal_move_options"' in text
