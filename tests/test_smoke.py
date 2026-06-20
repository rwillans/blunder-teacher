from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import chess
import chess.engine

from chess_analysis.critical_analysis import (
    CriticalPosition,
    LegalMoveOption,
    _analyse_legal_moves,
    _is_acceptable_alternative,
    _is_same_losing_bucket,
    _is_same_winning_bucket,
    extract_critical_positions,
)
from chess_analysis.pipeline import _filter_player_mistakes_only, run_pipeline
from chess_analysis.pgn_parser import parse_pgn_files
from chess_analysis.puzzles import assign_prompt_type, assign_puzzle_theme, assign_puzzle_themes, build_puzzles
from chess_analysis.puzzles import _build_prompt_hint
from chess_analysis.puzzles import _build_explanation
from chess_analysis.reporting import (
    PRIVATE_FIELD_NAMES,
    build_public_puzzle_payload,
    build_public_weakness_payload,
    build_puzzle_payload,
    write_puzzles_json,
    write_weaknesses_json,
    write_web_public_puzzles_json,
    write_web_public_weaknesses_json,
)
from chess_analysis.weaknesses import build_weakness_payload
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


def _eval_display(cp: float, mate: int | None = None) -> str:
    if mate is not None:
        return f"{'-' if mate < 0 else ''}M{abs(mate)}"
    return f"{cp / 100:+.2f}"


def _option_from_board(
    board: chess.Board,
    move_uci: str,
    mover_eval_cp: float,
    eval_loss_cp: float,
    grade: str = "Excellent",
    mover_mate: int | None = None,
    pv_uci: list[str] | None = None,
) -> LegalMoveOption:
    move = chess.Move.from_uci(move_uci)
    san = board.san(move)
    result_board = board.copy(stack=False)
    result_board.push(move)
    white_eval_cp = mover_eval_cp if board.turn == chess.WHITE else -mover_eval_cp
    white_mate = mover_mate if board.turn == chess.WHITE else (-mover_mate if mover_mate is not None else None)
    return LegalMoveOption(
        uci=move_uci,
        san=san,
        resulting_fen=result_board.fen(),
        eval_cp=white_eval_cp,
        eval_display=_eval_display(white_eval_cp, white_mate),
        mate=white_mate,
        pv_san=san,
        mover_eval_cp=mover_eval_cp,
        mover_eval_display=_eval_display(mover_eval_cp, mover_mate),
        mover_mate=mover_mate,
        eval_loss_cp=eval_loss_cp,
        eval_loss_display="Mate swing" if eval_loss_cp >= 100000 else f"{int(eval_loss_cp)} cp",
        grade=grade,
        pv_uci=pv_uci or [move_uci],
    )


def _critical_from_position(
    fen: str,
    best_uci: str,
    played_uci: str,
    best_mover_eval: float = 250.0,
    played_mover_eval: float = 0.0,
    eval_loss: float = 250.0,
    best_mover_mate: int | None = None,
    played_mover_mate: int | None = None,
    mate_related: bool = False,
    best_pv_uci: list[str] | None = None,
    played_pv_uci: list[str] | None = None,
) -> CriticalPosition:
    board = chess.Board(fen)
    best_option = _option_from_board(
        board,
        best_uci,
        best_mover_eval,
        0.0,
        mover_mate=best_mover_mate,
        pv_uci=best_pv_uci,
    )
    played_option = _option_from_board(
        board,
        played_uci,
        played_mover_eval,
        eval_loss,
        grade="Blunder" if eval_loss > 250 else "Mistake",
        mover_mate=played_mover_mate,
        pv_uci=played_pv_uci,
    )
    return CriticalPosition(
        source_file="a.pgn",
        game_index=1,
        event="E",
        site="S",
        date="2024.01.01",
        white="W",
        black="B",
        result="1-0",
        move_number=22,
        side_to_move="White" if board.turn == chess.WHITE else "Black",
        fen=fen,
        played_move=played_option.san,
        engine_best_move=best_option.san,
        eval_before=best_option.eval_cp,
        eval_after=played_option.eval_cp,
        eval_swing=eval_loss,
        mate_related=mate_related or best_mover_mate is not None or played_mover_mate is not None,
        eco="C20",
        opening="KP",
        played_move_uci=played_uci,
        engine_best_move_uci=best_uci,
        best_eval_display=best_option.eval_display,
        played_eval_display=played_option.eval_display,
        eval_loss_display=played_option.eval_loss_display,
        best_pv_san=best_option.pv_san,
        legal_move_options=[best_option, played_option],
    )


def test_pipeline_writes_web_first_puzzle_payload_by_default(tmp_path: Path) -> None:
    pgn_path = tmp_path / "sample.pgn"
    out_path = tmp_path / "out"
    pgn_path.write_text(BLUNDER_PGN, encoding="utf-8")

    run_pipeline(str(pgn_path), str(out_path), engine_depth=10, eval_threshold=120)

    assert (out_path / "puzzles.json").exists()
    assert (out_path / "weaknesses.json").exists()
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

    weaknesses = json.loads((out_path / "weaknesses.json").read_text(encoding="utf-8"))
    assert isinstance(weaknesses, list)


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


def test_main_forwards_theme_pv_plies(tmp_path: Path, monkeypatch) -> None:
    captured_kwargs: dict[str, object] = {}

    def fake_run_pipeline(*args, **kwargs):
        captured_kwargs.update(kwargs)
        return SimpleNamespace(
            pgn_file_count=0,
            records=[],
            critical_positions=[],
            puzzles=[],
            puzzles_json_path=str(tmp_path / "puzzles.json"),
            weaknesses_json_path=str(tmp_path / "weaknesses.json"),
            web_puzzles_json_path=None,
            web_weaknesses_json_path=None,
            engine_result=SimpleNamespace(success=True, detail="ok"),
        )

    monkeypatch.setattr("main.run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(sys, "argv", ["main.py", "--output", str(tmp_path), "--theme-pv-plies", "12"])

    assert main() == 0
    assert captured_kwargs["theme_pv_plies"] == 12


def test_main_rejects_invalid_theme_pv_plies(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["main.py", "--output", str(tmp_path), "--theme-pv-plies", "21"])

    assert main() == 2


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
    assert assign_prompt_type(_critical(80, -100, False)) == "Equalise"
    assert assign_prompt_type(_critical(-120, -150, False)) == "Defend accurately"
    assert assign_prompt_type(_critical(50, 0, False)) == "Find the best continuation"
    assert assign_prompt_type(_critical(100, -100000, True)) == "Avoid checkmate"


def test_prompt_assignment_logic_for_black_uses_white_oriented_eval() -> None:
    assert assign_prompt_type(_critical(503, 691, False, side_to_move="Black")) == "Defend accurately"


def test_prompt_assignment_uses_theme_driven_categories() -> None:
    mate = _critical_from_position(
        "6k1/8/6K1/8/8/8/8/7Q w - - 0 1",
        "h1a8",
        "h1a1",
        best_mover_eval=100000.0,
        played_mover_eval=500.0,
        eval_loss=100000.0,
        best_mover_mate=1,
    )
    assert assign_prompt_type(mate) == "Deliver checkmate"

    promotion = _critical_from_position(
        "4k3/P7/8/8/8/8/8/4K3 w - - 0 1",
        "a7a8q",
        "e1e2",
        best_mover_eval=900.0,
        played_mover_eval=100.0,
        eval_loss=800.0,
    )
    assert assign_prompt_type(promotion) == "Promote the pawn"

    quiet = _critical_from_position(
        "4k3/8/8/8/8/8/3R4/4K3 w - - 0 1",
        "d2d4",
        "d2d3",
        best_mover_eval=180.0,
        played_mover_eval=-120.0,
        eval_loss=300.0,
    )
    assert assign_prompt_type(quiet) == "Find the quiet resource"


def test_theme_assignment_covers_mate_promotion_quiet_and_fork() -> None:
    mate = _critical_from_position(
        "6k1/8/6K1/8/8/8/8/7Q w - - 0 1",
        "h1a8",
        "h1a1",
        best_mover_eval=100000.0,
        played_mover_eval=500.0,
        eval_loss=100000.0,
        best_mover_mate=1,
    )
    assert assign_puzzle_theme(mate) == "Mate in 1"
    assert "Checkmate" in assign_puzzle_themes(mate)

    promotion = _critical_from_position(
        "4k3/P7/8/8/8/8/8/4K3 w - - 0 1",
        "a7a8q",
        "e1e2",
        best_mover_eval=900.0,
        played_mover_eval=100.0,
        eval_loss=800.0,
    )
    assert assign_puzzle_theme(promotion) == "Promotion"
    assert "Crushing" in assign_puzzle_themes(promotion)

    quiet = _critical_from_position(
        "4k3/8/8/8/8/8/3R4/4K3 w - - 0 1",
        "d2d4",
        "d2d3",
        best_mover_eval=180.0,
        played_mover_eval=-120.0,
        eval_loss=300.0,
    )
    assert assign_puzzle_theme(quiet) == "Quiet move"

    fork = _critical_from_position(
        "4k3/7q/8/8/4N3/8/8/4K3 w - - 0 1",
        "e4f6",
        "e4g5",
        best_mover_eval=600.0,
        played_mover_eval=100.0,
        eval_loss=500.0,
    )
    assert "Fork" in assign_puzzle_themes(fork)


def test_theme_assignment_marks_defensive_and_goal_themes() -> None:
    assert assign_puzzle_theme(_critical(-120, -150, False)) == "Defensive move"
    assert "Crushing" in assign_puzzle_themes(_critical(700, 200, False))
    assert "Advantage" in assign_puzzle_themes(_critical(250, 0, False))


def test_theme_assignment_scans_later_best_line_moves() -> None:
    critical = _critical_from_position(
        "4k3/P7/8/8/8/8/8/4K3 w - - 0 1",
        "e1e2",
        "e1d1",
        best_mover_eval=900.0,
        played_mover_eval=100.0,
        eval_loss=800.0,
        best_pv_uci=["e1e2", "e8d8", "a7a8q"],
    )

    assert "Promotion" in assign_puzzle_themes(critical)


def test_theme_assignment_marks_back_rank_mate_from_replayed_line() -> None:
    critical = _critical_from_position(
        "6k1/5ppp/8/8/8/8/8/4R1K1 w - - 0 1",
        "e1e8",
        "e1e7",
        best_mover_eval=100000.0,
        played_mover_eval=500.0,
        eval_loss=100000.0,
        best_mover_mate=1,
        best_pv_uci=["e1e8"],
    )

    themes = assign_puzzle_themes(critical)

    assert "Checkmate" in themes
    assert "Back rank mate" in themes


def test_theme_assignment_marks_capture_the_defender_from_replayed_line() -> None:
    critical = _critical_from_position(
        "4k3/8/2n3p1/4q2Q/8/8/6B1/6K1 w - - 0 1",
        "g2c6",
        "g1h1",
        best_mover_eval=900.0,
        played_mover_eval=100.0,
        eval_loss=800.0,
        best_pv_uci=["g2c6", "e8f8", "h5e5"],
    )

    assert "Capture the defender" in assign_puzzle_themes(critical)


def test_legal_move_analysis_expands_only_best_and_played_pvs() -> None:
    class FakeEngine:
        def analyse(self, board, limit):
            move_uci = board.peek().uci()
            mover_eval = 500 if move_uci == "d2d4" else 120
            pv = [
                chess.Move.from_uci("a2a3"),
                chess.Move.from_uci("a7a6"),
                chess.Move.from_uci("a3a4"),
                chess.Move.from_uci("a6a5"),
                chess.Move.from_uci("a4a5"),
                chess.Move.from_uci("h7h6"),
                chess.Move.from_uci("h2h3"),
            ]
            return {"score": chess.engine.PovScore(chess.engine.Cp(-mover_eval), board.turn), "pv": pv}

    board = chess.Board("4k3/8/8/8/8/8/3R4/4K3 w - - 0 1")

    options = _analyse_legal_moves(
        FakeEngine(),
        board,
        chess.engine.Limit(depth=1),
        played_move_uci="d2d3",
        theme_pv_plies=8,
    )
    options_by_uci = {option.uci: option for option in options}
    untouched_option = next(option for option in options if option.uci not in {"d2d4", "d2d3"})

    assert len(options_by_uci["d2d4"].pv_uci) == 8
    assert len(options_by_uci["d2d3"].pv_uci) == 8
    assert len(untouched_option.pv_uci) == 6


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
    assert payload[0]["puzzle_theme"] == puzzles[0].puzzle_theme
    assert payload[0]["tags"]
    assert "legal_move_options" in payload[0]
    assert "pv_uci" in payload[0]["legal_move_options"][0]


def test_puzzle_ids_are_stable_across_repeated_builds() -> None:
    critical = _critical(150.0, 0.0, False)
    critical.game_id = "stable-game"

    first = build_puzzles([critical])[0]
    second = build_puzzles([critical])[0]

    assert first.puzzle_id == second.puzzle_id
    assert first.puzzle_id.startswith("puzzle_")
    assert first.puzzle_id != "puzzle_00001"


def test_puzzle_ids_do_not_depend_on_input_order_or_earlier_puzzles() -> None:
    earlier = _critical(300.0, 0.0, False, white="Earlier", black="Player")
    earlier.game_id = "earlier-game"
    first = _critical(150.0, 0.0, False, white="A", black="B")
    first.game_id = "first-game"
    second = _critical(220.0, -100.0, False, white="C", black="D")
    second.game_id = "second-game"

    original_ids = {p.white: p.puzzle_id for p in build_puzzles([first, second])}
    reordered_ids = {p.white: p.puzzle_id for p in build_puzzles([second, first])}
    with_earlier_ids = {p.white: p.puzzle_id for p in build_puzzles([earlier, first, second])}

    assert reordered_ids["A"] == original_ids["A"]
    assert reordered_ids["C"] == original_ids["C"]
    assert with_earlier_ids["A"] == original_ids["A"]
    assert with_earlier_ids["C"] == original_ids["C"]


def test_puzzle_ids_distinguish_different_games_with_same_fen() -> None:
    left = _critical(150.0, 0.0, False, white="A", black="B")
    left.game_id = "left-game"
    right = _critical(150.0, 0.0, False, white="A", black="B")
    right.game_id = "right-game"

    left_puzzle, right_puzzle = build_puzzles([left, right])

    assert left_puzzle.fen == right_puzzle.fen
    assert left_puzzle.puzzle_id != right_puzzle.puzzle_id


def test_puzzle_ids_ignore_engine_evaluation_and_annotation_fields() -> None:
    critical = _critical(150.0, 0.0, False)
    critical.game_id = "stable-game"
    changed_analysis = replace(
        critical,
        eval_before=900.0,
        eval_after=-300.0,
        eval_swing=1200.0,
        best_eval_display="+9.00",
        played_eval_display="-3.00",
        eval_loss_display="1200 cp",
        best_pv_san="Nf3 Nc6 d4",
        opening="Different opening label",
    )

    assert build_puzzles([critical])[0].puzzle_id == build_puzzles([changed_analysis])[0].puzzle_id


def test_stable_game_identity_does_not_shift_when_earlier_game_is_added(tmp_path: Path) -> None:
    target_game = """[Event "Target"]
[Site "Internet"]
[Date "2024.03.01"]
[Round "1"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 1-0
"""
    earlier_game = """[Event "Earlier"]
[Site "Internet"]
[Date "2024.02.01"]
[Round "1"]
[White "Carol"]
[Black "Dave"]
[Result "0-1"]

1. d4 d5 0-1

"""
    original_path = tmp_path / "original.pgn"
    shifted_path = tmp_path / "shifted.pgn"
    original_path.write_text(target_game, encoding="utf-8")
    shifted_path.write_text(earlier_game + target_game, encoding="utf-8")

    original_target = parse_pgn_files([original_path])[0].metadata
    shifted_target = next(record.metadata for record in parse_pgn_files([shifted_path]) if record.metadata.event == "Target")

    assert original_target.game_id == shifted_target.game_id
    assert original_target.game_index != shifted_target.game_index


def test_pv_uci_exports_replayable_best_line() -> None:
    critical = _critical_from_position(
        "4k3/8/8/8/8/8/3R4/4K3 w - - 0 1",
        "d2d4",
        "d2d3",
        best_mover_eval=180.0,
        played_mover_eval=-120.0,
        eval_loss=300.0,
    )
    critical.legal_move_options[0].pv_uci = ["d2d4", "e8e7"]
    puzzle = build_puzzles([critical])[0]
    payload = build_puzzle_payload([puzzle])
    pv_uci = payload[0]["legal_move_options"][0]["pv_uci"]

    board = chess.Board(critical.fen)
    for move_uci in pv_uci:
        move = chess.Move.from_uci(move_uci)
        assert move in board.legal_moves
        board.push(move)


def test_write_weaknesses_json_exports_ranked_groups(tmp_path: Path) -> None:
    puzzles = build_puzzles(
        [
            _critical(150.0, -50.0, False, white="Rob Willans", black="Other", side_to_move="White"),
            _critical(220.0, -180.0, False, white="Rob Willans", black="Other", side_to_move="White"),
            _critical(-120.0, -400.0, False, white="Rob Willans", black="Other", side_to_move="Black"),
        ]
    )

    json_path = write_weaknesses_json(tmp_path, puzzles)
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert json_path.name == "weaknesses.json"
    assert payload
    assert payload[0]["weakness_score"] >= payload[-1]["weakness_score"]
    assert any(item["group_type"] == "theme" for item in payload)
    assert any(item["group_type"] == "opening" and item["label"] == "KP" for item in payload)


def test_build_weakness_payload_counts_examples_and_mate_losses() -> None:
    mate_puzzle = build_puzzles(
        [
            _critical_from_position(
                "6k1/8/6K1/8/8/8/8/7Q w - - 0 1",
                "h1a8",
                "h1a1",
                best_mover_eval=100000.0,
                played_mover_eval=500.0,
                eval_loss=100000.0,
                best_mover_mate=1,
            )
        ]
    )[0]

    payload = build_weakness_payload([mate_puzzle])
    checkmate_group = next(item for item in payload if item["group_type"] == "theme" and item["label"] == "Checkmate")

    assert checkmate_group["count"] == 1
    assert checkmate_group["mate_loss_count"] == 1
    assert checkmate_group["puzzle_ids"] == [mate_puzzle.puzzle_id]
    assert checkmate_group["examples"][0]["id"] == mate_puzzle.puzzle_id


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


def _json_keys(value: object) -> set[str]:
    if isinstance(value, list):
        return set().union(*(_json_keys(item) for item in value)) if value else set()
    if isinstance(value, dict):
        return set(value).union(*(_json_keys(item) for item in value.values()))
    return set()


def test_public_puzzle_payload_removes_game_identifying_metadata() -> None:
    critical = _critical(
        150.0,
        0.0,
        False,
        white="PrivatePersonOne",
        black="PrivatePersonTwo",
        side_to_move="White",
    )
    critical.event = "PrivateTournament"
    critical.site = "PrivateVenue"
    critical.date = "2099.12.31"
    critical.result = "PrivateResult"
    critical.source_file = r"C:\Users\name\games\private-game.pgn"
    critical.game_index = 99
    puzzle = build_puzzles([critical])[0]

    full_payload = build_puzzle_payload([puzzle])
    public_payload = build_public_puzzle_payload([puzzle])
    public_text = json.dumps(public_payload)

    assert PRIVATE_FIELD_NAMES.issubset(full_payload[0])
    assert not (PRIVATE_FIELD_NAMES & _json_keys(public_payload))
    for private_value in [
        "PrivatePersonOne",
        "PrivatePersonTwo",
        "PrivateTournament",
        "PrivateVenue",
        "2099.12.31",
        "PrivateResult",
        "private-game.pgn",
        r"C:\Users\name",
    ]:
        assert private_value not in public_text
    assert public_payload[0]["id"] == puzzle.puzzle_id
    assert public_payload[0]["fen"] == puzzle.fen
    assert public_payload[0]["legal_move_options"]


def test_public_weakness_payload_keeps_group_data_without_examples_or_private_fields() -> None:
    critical = _critical(150.0, -50.0, False, white="PrivatePersonOne", black="PrivatePersonTwo")
    critical.event = "PrivateTournament"
    critical.site = "PrivateVenue"
    critical.date = "2099.12.31"
    critical.source_file = "/Users/name/private-game.pgn"
    puzzle = build_puzzles([critical])[0]

    public_payload = build_public_weakness_payload([puzzle])
    public_text = json.dumps(public_payload)

    assert public_payload
    assert not (PRIVATE_FIELD_NAMES & _json_keys(public_payload))
    assert "examples" not in _json_keys(public_payload)
    assert "latest_seen" not in _json_keys(public_payload)
    assert puzzle.puzzle_id in public_payload[0]["puzzle_ids"]
    for private_value in [
        "PrivatePersonOne",
        "PrivatePersonTwo",
        "PrivateTournament",
        "PrivateVenue",
        "2099.12.31",
        "private-game.pgn",
        "/Users/name",
    ]:
        assert private_value not in public_text


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
    assert not (PRIVATE_FIELD_NAMES & _json_keys(payload))


def test_write_web_public_weaknesses_json_syncs_reduced_payload_when_web_dir_exists(tmp_path: Path) -> None:
    puzzles = build_puzzles(
        [
            _critical(150.0, 0.0, False, white="Rob Willans", black="Other", side_to_move="White"),
        ]
    )
    (tmp_path / "web").mkdir()

    json_path = write_web_public_weaknesses_json(tmp_path, puzzles)

    assert json_path == tmp_path / "web" / "public" / "weaknesses.json"
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload
    assert not (PRIVATE_FIELD_NAMES & _json_keys(payload))
    assert "examples" not in _json_keys(payload)


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
