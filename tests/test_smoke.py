from __future__ import annotations

import json
import sys
from pathlib import Path

from chess_analysis.critical_analysis import (
    CriticalPosition,
    LegalMoveOption,
    _is_acceptable_alternative,
    _is_same_losing_bucket,
    _is_same_winning_bucket,
    extract_critical_positions,
)
from chess_analysis.engine_check import EngineCheckResult
from chess_analysis.pipeline import _filter_player_mistakes_only, run_pipeline
from chess_analysis.puzzles import assign_prompt_type, build_puzzles
from chess_analysis.puzzles import _build_prompt_hint
from chess_analysis.puzzles import _build_explanation
from chess_analysis.reporting import (
    build_puzzle_payload,
    write_puzzle_report_html,
    write_puzzles_json,
    write_summary_report_md,
    write_web_public_puzzles_json,
)
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
                mate=None,
                pv_san="Nf3 Nc6",
                mover_eval_cp=eval_before,
                mover_eval_display=f"{eval_before / 100:+.2f}",
                mover_mate=None,
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
                mate=None,
                pv_san="Qh5 Nc6",
                mover_eval_cp=eval_after,
                mover_eval_display=f"{eval_after / 100:+.2f}",
                mover_mate=None,
                eval_loss_cp=eval_before - eval_after,
                eval_loss_display=f"{int(eval_before - eval_after)} cp",
                grade="Blunder" if eval_before - eval_after > 250 else "Mistake",
            ),
        ],
    )


def test_pipeline_writes_web_first_puzzle_payload_by_default(tmp_path: Path) -> None:
    pgn_path = tmp_path / "sample.pgn"
    out_path = tmp_path / "out"
    pgn_path.write_text(BLUNDER_PGN, encoding="utf-8")

    run_pipeline(str(pgn_path), str(out_path), engine_depth=10, eval_threshold=120)

    assert (out_path / "puzzles.json").exists()
    assert not (out_path / "games_summary.csv").exists()
    assert not (out_path / "critical_positions.csv").exists()
    assert not (out_path / "summary_report.md").exists()
    assert not (out_path / "puzzles.csv").exists()
    assert not (out_path / "puzzles.html").exists()

    payload = json.loads((out_path / "puzzles.json").read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert payload
    assert payload[0]["best_move_uci"]
    assert payload[0]["legal_move_options"]


def test_default_inputs_directory_when_input_omitted(tmp_path: Path, monkeypatch) -> None:
    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir()
    (inputs_dir / "one.pgn").write_text(SAMPLE_PGN, encoding="utf-8")

    out_dir = tmp_path / "out"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["main.py", "--output", str(out_dir), "--engine-depth", "8"])

    code = main()
    assert code == 0
    assert (out_dir / "puzzles.json").exists()


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

    payload = json.loads((out_path / "puzzles.json").read_text(encoding="utf-8"))

    assert len(payload) == 1
    assert payload[0]["side_to_move"] == "White"


def test_prompt_assignment_logic() -> None:
    assert assign_prompt_type(_critical(80, -100, False)) == "Spot the danger"
    assert assign_prompt_type(_critical(-120, -150, False)) == "Defend accurately"
    assert assign_prompt_type(_critical(50, 0, False)) == "Find the best move"
    assert assign_prompt_type(_critical(100, -100000, True)) == "Spot the danger"


def test_prompt_assignment_logic_for_black_uses_white_oriented_eval() -> None:
    assert assign_prompt_type(_critical(503, 691, False, side_to_move="Black")) == "Defend accurately"


def test_extract_critical_positions_handles_missing_engine() -> None:
    critical = extract_critical_positions([], engine_path="/definitely/missing/stockfish")
    assert critical == []


def test_acceptable_alternative_for_near_equal_cp_move() -> None:
    best = LegalMoveOption("a1a8", "Ra8", "fen1", 120.0, "+1.20", None, "Ra8 Ra7", 120.0, "+1.20", None, 0.0, "0 cp", "Excellent")
    played = LegalMoveOption("a1a6", "Ra6", "fen2", 98.0, "+0.98", None, "Ra6 Ra7", 98.0, "+0.98", None, 22.0, "22 cp", "Good")

    assert _is_acceptable_alternative(best, played)


def test_acceptable_alternative_for_slightly_slower_mate() -> None:
    best = LegalMoveOption("c5c6", "Rc6", "fen1", 100000.0, "M8", 8, "Rc6 Kb7", 100000.0, "M8", 8, 0.0, "0 cp", "Excellent")
    played = LegalMoveOption("c5c8", "Rc8+", "fen2", 100000.0, "M10", 10, "Rc8+ Kb7", 100000.0, "M10", 10, 0.0, "0 cp", "Excellent")

    assert _is_acceptable_alternative(best, played)


def test_same_losing_bucket_filter_matches_broad_rule() -> None:
    assert _is_same_losing_bucket(-756.0, 265.0)
    assert not _is_same_losing_bucket(-499.0, 265.0)
    assert not _is_same_losing_bucket(-756.0, 301.0)


def test_same_winning_bucket_filter_matches_broad_rule() -> None:
    best = LegalMoveOption("e1e7", "Re7+", "fen1", 790.0, "+7.90", None, "Re7+ Kh6", 790.0, "+7.90", None, 0.0, "0 cp", "Excellent")
    played = LegalMoveOption("d6d3", "Rd3", "fen2", 550.0, "+5.50", None, "Rd3 Rc2+", 550.0, "+5.50", None, 250.0, "250 cp", "Mistake")

    assert _is_same_winning_bucket(best, played, 790.0, 550.0)
    assert not _is_same_winning_bucket(best, played, 490.0, 550.0)


def test_same_winning_bucket_filter_allows_slower_forced_mate() -> None:
    best = LegalMoveOption("g3g4", "Kg4", "fen1", 100000.0, "M6", 6, "Kg4 Ke5", 100000.0, "M6", 6, 0.0, "0 cp", "Excellent")
    played = LegalMoveOption("g3h4", "Kxh4", "fen2", 100000.0, "M13", 13, "Kxh4 Ke5", 100000.0, "M13", 13, 100000.0, "Mate swing", "Blunder")

    assert _is_same_winning_bucket(best, played, 100000.0, 100000.0)


def test_pipeline_does_not_crash_when_engine_missing_for_critical(tmp_path: Path, monkeypatch) -> None:
    pgn_path = tmp_path / "sample.pgn"
    out_path = tmp_path / "out"
    pgn_path.write_text(SAMPLE_PGN, encoding="utf-8")

    monkeypatch.setenv("STOCKFISH_PATH", "/definitely/missing/stockfish")
    result = run_pipeline(str(pgn_path), str(out_path), engine_depth=8, eval_threshold=150)

    assert len(result.records) == 2
    assert result.critical_positions == []
    assert result.puzzles == []
    assert (out_path / "puzzles.json").exists()


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
    assert "Played in Game" in text
    assert '"legal_move_options"' in text
    assert "renderPieceImage" in text
    assert "pieces/cburnett/wK.svg" in text
    assert "const nameMap = { k: 'king'" in text
    assert "const nameMap = {{ k: 'king'" not in text
    assert 'class="board-frame"' in text
    assert "♔" not in text


def test_write_puzzles_json_exports_frontend_friendly_payload(tmp_path: Path) -> None:
    puzzles = build_puzzles(
        [
            _critical(150.0, 0.0, False, white="Rob Willans", black="Other", side_to_move="White"),
        ]
    )

    json_path = write_puzzles_json(tmp_path, puzzles)
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert json_path.name == "puzzles.json"
    assert len(payload) == 1
    assert payload[0]["id"] == puzzles[0].puzzle_id
    assert payload[0]["fen"] == puzzles[0].fen
    assert payload[0]["best_move_uci"] == puzzles[0].best_move_uci
    assert payload[0]["prompt_hint"] == puzzles[0].prompt_hint
    assert "legal_move_options" in payload[0]


def test_build_puzzle_payload_matches_json_shape() -> None:
    puzzles = build_puzzles(
        [
            _critical(150.0, 0.0, False, white="Rob Willans", black="Other", side_to_move="White"),
        ]
    )

    payload = build_puzzle_payload(puzzles)

    assert payload[0]["id"] == puzzles[0].puzzle_id
    assert payload[0]["opening"] == puzzles[0].opening
    assert payload[0]["legal_move_options"]


def test_write_web_public_puzzles_json_syncs_payload_when_web_dir_exists(tmp_path: Path) -> None:
    puzzles = build_puzzles(
        [
            _critical(150.0, 0.0, False, white="Rob Willans", black="Other", side_to_move="White"),
        ]
    )
    (tmp_path / "web").mkdir()

    json_path = write_web_public_puzzles_json(tmp_path, puzzles)

    assert json_path == tmp_path / "web" / "public" / "puzzles.json"
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload[0]["id"] == puzzles[0].puzzle_id


def test_build_explanation_for_find_best_move_mentions_status_rank_and_pv() -> None:
    critical = _critical(180.0, 10.0, False, side_to_move="White")
    critical.best_pv_san = "Nf3 Nc6 d4"

    explanation = _build_explanation(critical, "Find the best move")

    assert "White was better before the mistake" in explanation
    assert "Nf3 kept the stronger continuation" in explanation
    assert "Qh5 gives up too much" in explanation
    assert "2nd among 2 legal moves" in explanation
    assert "A useful engine line is Nf3 Nc6 d4." in explanation


def test_build_prompt_hint_mentions_material_loss_for_generic_blunder() -> None:
    critical = _critical(180.0, -180.0, False, side_to_move="White")

    hint = _build_prompt_hint(critical, "Find the best move")

    assert hint == "Hint: Qh5 loses material or allows a decisive attack."


def test_build_prompt_hint_does_not_inherit_best_move_material_win() -> None:
    critical = _critical(300.0, 100.0, False, side_to_move="White")
    critical.fen = "3qk3/8/8/8/8/8/4P3/3QK3 w - - 0 1"
    critical.engine_best_move = "Qxd8+"
    critical.engine_best_move_uci = "d1d8"
    critical.played_move = "e4"
    critical.played_move_san = "e4"
    critical.played_move_uci = "e2e4"
    critical.legal_move_options = [
        LegalMoveOption("d1d8", "Qxd8+", "3Qk4/8/8/8/8/8/4P3/4K3 b - - 0 1", 300.0, "+3.00", None, "Qxd8+", 300.0, "+3.00", None, 0.0, "0 cp", "Excellent"),
        LegalMoveOption("e2e4", "e4", "3qk3/8/8/8/4P3/8/8/3QK3 b - - 0 1", 100.0, "+1.00", None, "e4", 100.0, "+1.00", None, 200.0, "200 cp", "Mistake"),
    ]

    hint = _build_prompt_hint(critical, "Find the best move")

    assert hint == "Hint: e4 gives away too much and worsens the position."


def test_build_explanation_for_defence_mentions_pressure_and_worst_move() -> None:
    critical = _critical(220.0, 520.0, False, side_to_move="Black")
    critical.played_move = "Qh5??"
    critical.played_move_san = "Qh5??"
    critical.played_move_uci = "d1h5"
    critical.engine_best_move = "Kg7"
    critical.engine_best_move_uci = "g8g7"
    critical.best_eval_display = "+2.20"
    critical.played_eval_display = "+5.20"
    critical.eval_loss_display = "300 cp"
    critical.best_pv_san = "Kg7 Qf3"
    critical.legal_move_options = [
        LegalMoveOption("g8g7", "Kg7", "fen-1", 220.0, "+2.20", None, "Kg7 Qf3", -220.0, "-2.20", None, 0.0, "0 cp", "Excellent"),
        LegalMoveOption("f8e7", "Be7", "fen-2", 120.0, "+1.20", None, "Be7 Qf3", -120.0, "-1.20", None, 100.0, "100 cp", "Inaccuracy"),
        LegalMoveOption("d1h5", "Qh5??", "fen-3", 520.0, "+5.20", None, "Qh5?? Qxh5", -520.0, "-5.20", None, 300.0, "300 cp", "Blunder"),
    ]

    explanation = _build_explanation(critical, "Defend accurately")

    assert "Black was worse before the mistake" in explanation
    assert "Kg7 was the cleanest defensive try" in explanation
    assert "Qh5?? failed to stabilise the position" in explanation
    assert "major error" in explanation
    assert "worst of the 3 legal moves" in explanation


def test_build_prompt_hint_mentions_failed_defence() -> None:
    critical = _critical(220.0, 520.0, False, side_to_move="Black")
    critical.played_move = "Qh5??"
    critical.played_move_san = "Qh5??"
    critical.played_move_uci = "d1h5"
    critical.engine_best_move = "Kg7"
    critical.engine_best_move_uci = "g8g7"
    critical.best_eval_display = "+2.20"
    critical.played_eval_display = "+5.20"
    critical.eval_loss_display = "300 cp"
    critical.legal_move_options = [
        LegalMoveOption("g8g7", "Kg7", "fen-1", 220.0, "+2.20", None, "Kg7 Qf3", -220.0, "-2.20", None, 0.0, "0 cp", "Excellent"),
        LegalMoveOption("d1h5", "Qh5??", "fen-3", 520.0, "+5.20", None, "Qh5?? Qxh5", -520.0, "-5.20", None, 300.0, "300 cp", "Blunder"),
    ]

    hint = _build_prompt_hint(critical, "Defend accurately")

    assert hint == "Hint: Qh5?? fails to hold the position and loses material or the attack."


def test_build_explanation_for_mate_related_position_mentions_forced_mate() -> None:
    critical = _critical(100000.0, -100000.0, True, side_to_move="White")
    critical.engine_best_move = "Qg7#"
    critical.engine_best_move_uci = "g6g7"
    critical.best_eval_display = "M1"
    critical.played_move = "Qh6??"
    critical.played_move_san = "Qh6??"
    critical.played_move_uci = "g6h6"
    critical.played_eval_display = "-M2"
    critical.eval_loss_display = "Mate swing"
    critical.best_pv_san = "Qg7#"
    critical.legal_move_options = [
        LegalMoveOption("g6g7", "Qg7#", "fen-best", 100000.0, "M1", 1, "Qg7#", 100000.0, "M1", 1, 0.0, "0 cp", "Excellent"),
        LegalMoveOption("g6h6", "Qh6??", "fen-played", -100000.0, "-M2", -2, "Qh6?? Kf7", -100000.0, "-M2", -2, 100000.0, "Mate swing", "Blunder"),
    ]

    explanation = _build_explanation(critical, "Spot the danger")

    assert "White was winning before the mistake" in explanation
    assert "Qg7# was a forcing move" in explanation
    assert "Qh6?? allows a forced mate" in explanation
    assert "decisive error" in explanation


def test_build_prompt_hint_mentions_forced_mate() -> None:
    critical = _critical(100000.0, -100000.0, True, side_to_move="White")
    critical.engine_best_move = "Qg7#"
    critical.engine_best_move_uci = "g6g7"
    critical.played_move = "Qh6??"
    critical.played_move_san = "Qh6??"
    critical.played_move_uci = "g6h6"
    critical.legal_move_options = [
        LegalMoveOption("g6g7", "Qg7#", "fen-best", 100000.0, "M1", 1, "Qg7#", 100000.0, "M1", 1, 0.0, "0 cp", "Excellent"),
        LegalMoveOption("g6h6", "Qh6??", "fen-played", -100000.0, "-M2", -2, "Qh6?? Kf7", -100000.0, "-M2", -2, 100000.0, "Mate swing", "Blunder"),
    ]

    hint = _build_prompt_hint(critical, "Spot the danger")

    assert hint == "Hint: Qh6?? allows a forced mate."
