from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List

import chess
import chess.engine
import chess.pgn

from .engine_check import DEFAULT_STOCKFISH_PATH
from .pgn_parser import GameRecord


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

                    eval_before = _score_to_cp(pre_score, turn_before)
                    pv = pre_info.get("pv")
                    best_move = board.san(pv[0]) if pv else ""

                    played_move_san = board.san(move)
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

                    eval_after = -_score_to_cp(post_score, board.turn)
                    swing = eval_before - eval_after
                    mate_related = bool(pre_score.is_mate() or post_score.is_mate())

                    if swing >= eval_threshold:
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
                                engine_best_move=best_move,
                                eval_before=float(eval_before),
                                eval_after=float(eval_after),
                                eval_swing=float(swing),
                                mate_related=mate_related,
                                eco=metadata.eco,
                                opening=metadata.opening,
                            )
                        )
    except FileNotFoundError:
        logging.warning("Engine binary not found for critical analysis: %s", engine_path)
    except Exception as exc:
        logging.warning("Critical analysis failed to start: %s", exc)

    return critical_positions
