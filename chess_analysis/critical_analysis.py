from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Iterable, List

import chess
import chess.engine
import chess.pgn

from .engine_check import DEFAULT_STOCKFISH_PATH
from .pgn_parser import GameRecord


@dataclass
class LegalMoveOption:
    uci: str
    san: str
    resulting_fen: str
    eval_cp: float
    eval_display: str
    eval_loss_cp: float
    eval_loss_display: str
    grade: str


@dataclass
class EvalSummary:
    cp: int
    display: str
    mate: int | None


@dataclass
class CriticalPosition:
    source_file: str
    game_index: int
    event: str
    site: str
    date: str
    white: str
    black: str
    result: str
    move_number: int
    side_to_move: str
    fen: str
    played_move: str
    engine_best_move: str
    eval_before: float
    eval_after: float
    eval_swing: float
    mate_related: bool
    eco: str
    opening: str
    played_move_uci: str = ""
    engine_best_move_uci: str = ""
    best_eval_display: str = ""
    played_eval_display: str = ""
    eval_loss_display: str = ""
    best_pv_san: str = ""
    legal_move_options: list[LegalMoveOption] = field(default_factory=list)


def _score_to_cp(score: chess.engine.PovScore, turn: chess.Color) -> int:
    # Normalize to centipawns from side-to-move perspective.
    normalized = score.pov(turn)
    if normalized.is_mate():
        mate_in = normalized.mate()
        if mate_in is None:
            return 0
        # Map mate scores to large cp values for thresholding/reporting.
        return 100000 if mate_in > 0 else -100000
    cp = normalized.score()
    return cp if cp is not None else 0


def _format_eval_display(cp: int, mate: int | None) -> str:
    if mate is not None:
        return f"{'-' if mate < 0 else ''}M{abs(mate)}"
    return f"{cp / 100:+.2f}"


def _score_to_summary(score: chess.engine.PovScore, turn: chess.Color) -> EvalSummary:
    normalized = score.pov(turn)
    if normalized.is_mate():
        mate_in = normalized.mate()
        if mate_in is None:
            return EvalSummary(0, "M?", None)
        cp = 100000 if mate_in > 0 else -100000
        return EvalSummary(cp, _format_eval_display(cp, mate_in), mate_in)

    cp = normalized.score()
    cp_value = cp if cp is not None else 0
    return EvalSummary(cp_value, _format_eval_display(cp_value, None), None)


def _invert_summary(summary: EvalSummary) -> EvalSummary:
    mate = -summary.mate if summary.mate is not None else None
    cp = -summary.cp
    return EvalSummary(cp, _format_eval_display(cp, mate), mate)


def _format_eval_loss_display(eval_loss_cp: float) -> str:
    if eval_loss_cp >= 100000:
        return "Mate swing"
    return f"{int(eval_loss_cp)} cp"


def _grade_eval_loss(eval_loss_cp: float) -> str:
    if eval_loss_cp <= 20:
        return "Excellent"
    if eval_loss_cp <= 50:
        return "Good"
    if eval_loss_cp <= 120:
        return "Inaccuracy"
    if eval_loss_cp <= 250:
        return "Mistake"
    return "Blunder"


def _pv_to_san(board: chess.Board, pv: list[chess.Move] | None, max_plies: int = 6) -> str:
    if not pv:
        return ""

    preview_board = board.copy()
    san_moves: list[str] = []
    for move in pv[:max_plies]:
        try:
            san_moves.append(preview_board.san(move))
        except Exception:
            break
        preview_board.push(move)
    return " ".join(san_moves)


def _analyse_legal_moves(
    engine: chess.engine.SimpleEngine,
    board: chess.Board,
    limit: chess.engine.Limit,
    best_eval_cp: int,
) -> list[LegalMoveOption]:
    legal_move_options: list[LegalMoveOption] = []
    for legal_move in list(board.legal_moves):
        candidate_board = board.copy()
        candidate_san = board.san(legal_move)
        candidate_board.push(legal_move)

        try:
            candidate_info = engine.analyse(candidate_board, limit)
        except Exception as exc:
            logging.warning("Engine analysis failed for candidate move %s: %s", legal_move.uci(), exc)
            continue

        candidate_score = candidate_info.get("score")
        if candidate_score is None:
            continue

        candidate_summary = _invert_summary(_score_to_summary(candidate_score, candidate_board.turn))
        eval_loss_cp = max(0, best_eval_cp - candidate_summary.cp)
        legal_move_options.append(
            LegalMoveOption(
                uci=legal_move.uci(),
                san=candidate_san,
                resulting_fen=candidate_board.fen(),
                eval_cp=float(candidate_summary.cp),
                eval_display=candidate_summary.display,
                eval_loss_cp=float(eval_loss_cp),
                eval_loss_display=_format_eval_loss_display(eval_loss_cp),
                grade=_grade_eval_loss(eval_loss_cp),
            )
        )

    return legal_move_options


def extract_critical_positions(
    games: Iterable[tuple[GameRecord, chess.pgn.Game]],
    engine_path: str = DEFAULT_STOCKFISH_PATH,
    engine_depth: int = 14,
    eval_threshold: int = 150,
) -> List[CriticalPosition]:
    critical_positions: List[CriticalPosition] = []

    try:
        with chess.engine.SimpleEngine.popen_uci(engine_path) as engine:
            limit = chess.engine.Limit(depth=engine_depth)

            for metadata, game in games:
                board = game.board()
                for move in game.mainline_moves():
                    board_before = board.copy()
                    turn_before = board.turn
                    move_number = board.fullmove_number
                    fen_before = board.fen()

                    try:
                        pre_info = engine.analyse(board, limit)
                    except Exception as exc:
                        logging.warning(
                            "Engine analysis failed before move in game %s#%s: %s",
                            metadata.source_file,
                            metadata.game_index,
                            exc,
                        )
                        break

                    pre_score = pre_info.get("score")
                    if pre_score is None:
                        board.push(move)
                        continue

                    pre_summary = _score_to_summary(pre_score, turn_before)
                    eval_before = pre_summary.cp
                    pv = pre_info.get("pv")
                    best_move = board.san(pv[0]) if pv else ""
                    best_move_uci = pv[0].uci() if pv else ""
                    best_pv_san = _pv_to_san(board_before, pv)

                    played_move_san = board.san(move)
                    played_move_uci = move.uci()
                    board.push(move)

                    try:
                        post_info = engine.analyse(board, limit)
                    except Exception as exc:
                        logging.warning(
                            "Engine analysis failed after move in game %s#%s: %s",
                            metadata.source_file,
                            metadata.game_index,
                            exc,
                        )
                        break

                    post_score = post_info.get("score")
                    if post_score is None:
                        continue

                    played_summary = _invert_summary(_score_to_summary(post_score, board.turn))
                    eval_after = played_summary.cp
                    swing = eval_before - eval_after
                    mate_related = bool(pre_score.is_mate() or post_score.is_mate())

                    if swing >= eval_threshold:
                        legal_move_options = _analyse_legal_moves(engine, board_before, limit, eval_before)
                        critical_positions.append(
                            CriticalPosition(
                                source_file=metadata.source_file,
                                game_index=metadata.game_index,
                                event=metadata.event,
                                site=metadata.site,
                                date=metadata.date,
                                white=metadata.white,
                                black=metadata.black,
                                result=metadata.result,
                                move_number=move_number,
                                side_to_move="White" if turn_before == chess.WHITE else "Black",
                                fen=fen_before,
                                played_move=played_move_san,
                                played_move_uci=played_move_uci,
                                engine_best_move=best_move,
                                engine_best_move_uci=best_move_uci,
                                eval_before=float(eval_before),
                                eval_after=float(eval_after),
                                eval_swing=float(swing),
                                mate_related=mate_related,
                                eco=metadata.eco,
                                opening=metadata.opening,
                                best_eval_display=pre_summary.display,
                                played_eval_display=played_summary.display,
                                eval_loss_display=_format_eval_loss_display(swing),
                                best_pv_san=best_pv_san,
                                legal_move_options=legal_move_options,
                            )
                        )
    except FileNotFoundError:
        logging.warning("Engine binary not found for critical analysis: %s", engine_path)
    except Exception as exc:
        logging.warning("Critical analysis failed to start: %s", exc)

    return critical_positions
