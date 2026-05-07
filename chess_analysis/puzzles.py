from __future__ import annotations

import chess
from dataclasses import dataclass, field
from typing import Iterable, List
from urllib.parse import quote

from .critical_analysis import CriticalPosition, LegalMoveOption


@dataclass
class PuzzleRecord:
    puzzle_id: str
    fen: str
    side_to_move: str
    move_number: int
    prompt: str
    prompt_type: str
    recommended_focus: str
    notes_placeholder: str
    played_move: str
    engine_best_move: str
    eval_before_cp: float
    eval_after_cp: float
    eval_swing_cp: float
    is_mate_related: bool
    source_file: str
    game_index: int
    event: str
    site: str
    date: str
    white: str
    black: str
    result: str
    eco: str
    opening: str
    lichess_url: str = ""
    puzzle_prompt_type: str = ""
    puzzle_theme: str = ""
    best_move_uci: str = ""
    best_move_san: str = ""
    played_move_uci: str = ""
    played_move_san: str = ""
    best_eval: float = 0.0
    best_eval_display: str = ""
    played_eval: float = 0.0
    played_eval_display: str = ""
    eval_loss: float = 0.0
    eval_loss_display: str = ""
    best_pv: str = ""
    prompt_hint: str = ""
    explanation: str = ""
    tags: list[str] = field(default_factory=list)
    legal_move_options: list[LegalMoveOption] = field(default_factory=list)


def _eval_for_side(eval_cp: float, side_to_move: str) -> float:
    return eval_cp if side_to_move.strip().lower() == "white" else -eval_cp


def assign_prompt_type(critical: CriticalPosition) -> str:
    """Simple rule-based prompt selector for v1 puzzle export."""
    mover_eval_before = _eval_for_side(critical.eval_before, critical.side_to_move)
    mover_eval_after = _eval_for_side(critical.eval_after, critical.side_to_move)

    # Mate transitions are usually tactical danger moments.
    if critical.mate_related:
        return "Spot the danger"

    # Already under pressure before the move: emphasize defense.
    if mover_eval_before < -80:
        return "Defend accurately"

    # Not yet bad, but the played move allows a dangerous downturn.
    if mover_eval_after <= -100:
        return "Spot the danger"

    # Otherwise treat as a missed-improvement exercise.
    return "Find the best move"


def _safe_board(fen: str) -> chess.Board | None:
    try:
        return chess.Board(fen)
    except ValueError:
        return None


def _mate_theme(best_option: LegalMoveOption | None) -> str | None:
    if best_option is None or best_option.mate is None or best_option.mate <= 0:
        return None
    if best_option.mate == 1:
        return "Mate in 1"
    if best_option.mate == 2:
        return "Mate in 2"
    if best_option.mate == 3:
        return "Mate in 3"
    if best_option.mate == 4:
        return "Mate in 4"
    return "Mate in 5 or more"


def assign_puzzle_theme(critical: CriticalPosition) -> str:
    mover_eval_before = _eval_for_side(critical.eval_before, critical.side_to_move)
    best_option = _find_best_option(critical)
    mate_theme = _mate_theme(best_option)
    if mate_theme is not None:
        return mate_theme
    if critical.mate_related and mover_eval_before >= -80:
        return "Checkmate"
    if mover_eval_before < -80:
        return "Defensive move"
    if mover_eval_before >= 600:
        return "Crushing"
    if mover_eval_before >= 200:
        return "Advantage"
    return "Equality"


def _recommended_focus(prompt_type: str) -> str:
    if prompt_type == "Find the best move":
        return "candidate moves"
    if prompt_type == "Spot the danger":
        return "opponent threats"
    return "defence and damage control"


def _prompt_text(prompt_type: str, side_to_move: str) -> str:
    if prompt_type == "Find the best move":
        return f"{side_to_move} to move: Find the best move."
    if prompt_type == "Spot the danger":
        return f"{side_to_move} to move: Spot the danger and identify the critical threat."
    return f"{side_to_move} to move: Defend accurately and limit the damage."


def _lichess_analysis_url(fen: str, side_to_move: str) -> str:
    color = "white" if side_to_move.strip().lower() == "white" else "black"
    return f"https://lichess.org/analysis/{quote(fen, safe='/')}?color={color}"


def _build_tags(critical: CriticalPosition, prompt_type: str) -> list[str]:
    puzzle_theme = assign_puzzle_theme(critical)
    tags: list[str] = [puzzle_theme]
    for tag in _phase_tags(critical):
        if tag not in tags:
            tags.append(tag)
    for tag in _motif_tags(critical):
        if tag not in tags:
            tags.append(tag)
    if prompt_type == "Defend accurately" and "Defensive move" not in tags:
        tags.append("Defensive move")
    if critical.mate_related and not any(tag.startswith("Mate in") or tag == "Checkmate" for tag in tags):
        tags.append("Checkmate")
    return tags


def _phase_tags(critical: CriticalPosition) -> list[str]:
    board = _safe_board(critical.fen)
    if board is None:
        if critical.move_number <= 10:
            return ["Opening"]
        if critical.move_number >= 35:
            return ["Endgame"]
        return ["Middlegame"]

    queens = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(board.pieces(chess.QUEEN, chess.BLACK))
    rooks = len(board.pieces(chess.ROOK, chess.WHITE)) + len(board.pieces(chess.ROOK, chess.BLACK))
    bishops = len(board.pieces(chess.BISHOP, chess.WHITE)) + len(board.pieces(chess.BISHOP, chess.BLACK))
    knights = len(board.pieces(chess.KNIGHT, chess.WHITE)) + len(board.pieces(chess.KNIGHT, chess.BLACK))
    non_pawn_pieces = queens + rooks + bishops + knights

    if queens == 0 and non_pawn_pieces <= 4:
        if rooks > 0 and bishops == 0 and knights == 0:
            return ["Endgame", "Rook endgame"]
        if bishops > 0 and rooks == 0 and knights == 0:
            return ["Endgame", "Bishop endgame"]
        if knights > 0 and rooks == 0 and bishops == 0:
            return ["Endgame", "Knight endgame"]
        if rooks == 0 and bishops == 0 and knights == 0:
            return ["Endgame", "Pawn endgame"]
        return ["Endgame"]

    if queens > 0 and rooks == 0 and bishops == 0 and knights == 0:
        return ["Endgame", "Queen endgame"]
    if queens > 0 and rooks > 0 and bishops == 0 and knights == 0:
        return ["Endgame", "Queen and Rook"]
    if critical.move_number <= 10:
        return ["Opening"]
    return ["Middlegame"]


def _promotion_tag(move: chess.Move) -> str | None:
    if move.promotion is None:
        return None
    if move.promotion == chess.QUEEN:
        return "Promotion"
    return "Underpromotion"


def _capture_hanging_piece(board: chess.Board, move: chess.Move) -> bool:
    if not board.is_capture(move):
        return False
    target_piece = board.piece_at(move.to_square)
    if target_piece is None:
        return False
    target_color = target_piece.color
    defenders = board.attackers(target_color, move.to_square)
    return len(defenders) == 0


PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
}


def _material_balance(board: chess.Board, color: bool) -> int:
    own_score = 0
    opp_score = 0
    for piece_type, value in PIECE_VALUES.items():
        own_score += len(board.pieces(piece_type, color)) * value
        opp_score += len(board.pieces(piece_type, not color)) * value
    return own_score - opp_score


def _played_loses_material(critical: CriticalPosition, played_option: LegalMoveOption | None) -> bool:
    if played_option is None:
        return False
    board_before = _safe_board(critical.fen)
    board_after = _safe_board(played_option.resulting_fen)
    if board_before is None or board_after is None:
        return False
    mover_color = board_before.turn
    before_balance = _material_balance(board_before, mover_color)
    after_balance = _material_balance(board_after, mover_color)
    return after_balance <= before_balance - 1


def _fork_tag(board_after: chess.Board, move: chess.Move, mover_color: bool) -> bool:
    moved_piece = board_after.piece_at(move.to_square)
    if moved_piece is None:
        return False
    attacked_values: set[int] = set()
    attacked_king = False
    for square in board_after.attacks(move.to_square):
        piece = board_after.piece_at(square)
        if piece is None or piece.color == mover_color:
            continue
        if piece.piece_type == chess.KING:
            attacked_king = True
            continue
        if piece.piece_type != chess.PAWN:
            attacked_values.add(piece.piece_type)
    return attacked_king and bool(attacked_values) or len(attacked_values) >= 2


def _discovered_check(board: chess.Board, move: chess.Move) -> bool:
    mover_color = board.turn
    enemy_king_square = board.king(not mover_color)
    if enemy_king_square is None:
        return False
    board_before = board.copy(stack=False)
    board_before.push(move)
    if not board_before.is_check():
        return False

    source = move.from_square
    for attacker_square in board_before.attackers(mover_color, enemy_king_square):
        if attacker_square == move.to_square:
            continue
        attacker = board_before.piece_at(attacker_square)
        if attacker is None or attacker.color != mover_color:
            continue
        if attacker.piece_type in (chess.BISHOP, chess.ROOK, chess.QUEEN):
            ray = chess.SquareSet.between(attacker_square, enemy_king_square)
            if source in ray:
                return True
    return False


def _motif_tags(critical: CriticalPosition) -> list[str]:
    board = _safe_board(critical.fen)
    if board is None or not critical.engine_best_move_uci:
        return []
    try:
        move = chess.Move.from_uci(critical.engine_best_move_uci)
    except ValueError:
        return []
    if move not in board.legal_moves:
        return []

    mover_color = board.turn
    tags: list[str] = []
    promotion_tag = _promotion_tag(move)
    if promotion_tag is not None:
        tags.append(promotion_tag)
    if _capture_hanging_piece(board, move):
        tags.append("Hanging piece")
    if _discovered_check(board, move):
        tags.append("Discovered check")

    board_after = board.copy(stack=False)
    board_after.push(move)

    best_option = _find_best_option(critical)
    if best_option is not None and best_option.mate is not None and best_option.mate > 0 and "Checkmate" not in tags:
        tags.append("Checkmate")
    enemy_king_square = board_after.king(not mover_color)
    if enemy_king_square is not None and board_after.is_check() and board_after.attackers(mover_color, enemy_king_square):
        if "Checkmate" not in tags:
            tags.append("Exposed king")
    if _fork_tag(board_after, move, mover_color):
        tags.append("Fork")
    return tags


def _position_label(mover_eval_cp: float) -> str:
    if mover_eval_cp >= 500:
        return "winning"
    if mover_eval_cp >= 150:
        return "better"
    if mover_eval_cp > -120:
        return "roughly level"
    if mover_eval_cp > -500:
        return "worse"
    return "in serious trouble"


def _severity_label(eval_loss_cp: float) -> str:
    if eval_loss_cp >= 100000:
        return "decisive"
    if eval_loss_cp >= 300:
        return "major"
    if eval_loss_cp >= 120:
        return "serious"
    if eval_loss_cp >= 50:
        return "notable"
    return "small"


def _sorted_legal_options(critical: CriticalPosition) -> list[LegalMoveOption]:
    return sorted(
        critical.legal_move_options,
        key=lambda option: (float(option.eval_loss_cp), option.san, option.uci),
    )


def _find_played_option(critical: CriticalPosition) -> LegalMoveOption | None:
    return next(
        (option for option in critical.legal_move_options if option.uci == critical.played_move_uci),
        None,
    )


def _find_best_option(critical: CriticalPosition) -> LegalMoveOption | None:
    return next((option for option in critical.legal_move_options if float(option.eval_loss_cp) == 0.0), None)


def _played_rank_text(critical: CriticalPosition) -> str:
    played_option = _find_played_option(critical)
    if played_option is None or not critical.legal_move_options:
        return ""

    ranked = _sorted_legal_options(critical)
    try:
        played_rank = next(index for index, option in enumerate(ranked, start=1) if option.uci == played_option.uci)
    except StopIteration:
        return ""

    def ordinal(value: int) -> str:
        if 10 <= value % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
        return f"{value}{suffix}"

    total_options = len(ranked)
    if played_rank == 1:
        return "It was the engine's top choice."
    if played_rank == 2 and float(played_option.eval_loss_cp) <= 30.0:
        return "It was close to the best move, but still second-best."
    if played_rank == total_options and total_options > 2:
        return f"It was the worst of the {total_options} legal moves the engine checked."
    if played_rank > max(3, total_options // 2):
        return f"It landed only {ordinal(played_rank)} out of {total_options} legal moves."
    return f"It ranked {ordinal(played_rank)} among {total_options} legal moves."


def _best_plan_text(critical: CriticalPosition, best_option: LegalMoveOption | None, prompt_type: str) -> str:
    best_move = critical.engine_best_move or "the engine move"
    best_eval = critical.best_eval_display or f"{critical.eval_before / 100:+.2f}"

    if best_option is not None and best_option.mate is not None and best_option.mate > 0:
        return f"{best_move} was a forcing move: it keeps a mating attack with {best_option.eval_display}."

    if prompt_type == "Defend accurately":
        return f"{best_move} was the cleanest defensive try, keeping the position around {best_eval}."
    if prompt_type == "Spot the danger":
        return f"{best_move} was the critical move, holding the line at about {best_eval}."
    return f"{best_move} kept the stronger continuation and preserved roughly {best_eval}."


def _mistake_text(
    critical: CriticalPosition,
    prompt_type: str,
    mover_eval_after: float,
    played_option: LegalMoveOption | None,
) -> str:
    played_move = critical.played_move or "the game move"
    played_eval = critical.played_eval_display or f"{critical.eval_after / 100:+.2f}"

    if played_option is not None and played_option.mover_mate is not None and played_option.mover_mate < 0:
        return f"{played_move} allows a forced mate against the side to move."

    if critical.mate_related and mover_eval_after < 0:
        return f"{played_move} turns the position into a concrete tactical problem and drops the evaluation to {played_eval}."

    if prompt_type == "Defend accurately":
        return f"{played_move} failed to stabilise the position and left the side to move on {played_eval}."
    if prompt_type == "Spot the danger":
        return f"{played_move} misses the key threat and slides to {played_eval}."
    return f"{played_move} gives up too much compared with the best line and leaves the position on {played_eval}."


def _build_prompt_hint(critical: CriticalPosition, prompt_type: str) -> str:
    mover_eval_before = _eval_for_side(critical.eval_before, critical.side_to_move)
    mover_eval_after = _eval_for_side(critical.eval_after, critical.side_to_move)
    best_option = _find_best_option(critical)
    played_option = _find_played_option(critical)
    played_move = critical.played_move or "the game move"
    eval_loss_cp = float(played_option.eval_loss_cp) if played_option is not None else abs(float(critical.eval_swing))

    if played_option is not None and played_option.mover_mate is not None and played_option.mover_mate < 0:
        return f"Hint: {played_move} allows a forced mate."

    if best_option is not None and best_option.mate is not None and best_option.mate > 0:
        return f"Hint: {played_move} misses a forced mate."

    if _played_loses_material(critical, played_option):
        return f"Hint: {played_move} loses material."

    if prompt_type == "Defend accurately":
        if mover_eval_after <= -500 or eval_loss_cp >= 250:
            return f"Hint: {played_move} fails to hold the position and loses material or the attack."
        return f"Hint: {played_move} fails to find the needed defence."

    if eval_loss_cp >= 250:
        return f"Hint: {played_move} loses material or allows a decisive attack."

    if mover_eval_before >= -120 and mover_eval_after <= -120:
        return f"Hint: {played_move} turns a playable position into a worse one."

    if eval_loss_cp >= 120:
        return f"Hint: {played_move} gives away too much and worsens the position."

    return f"Hint: {played_move} is not accurate enough."


def _build_explanation(critical: CriticalPosition, prompt_type: str) -> str:
    mover_eval_before = _eval_for_side(critical.eval_before, critical.side_to_move)
    mover_eval_after = _eval_for_side(critical.eval_after, critical.side_to_move)
    opening_text = critical.opening or "this line"
    best_option = _find_best_option(critical)
    played_option = _find_played_option(critical)
    eval_loss_cp = (
        float(played_option.eval_loss_cp)
        if played_option is not None
        else abs(float(critical.eval_swing))
    )
    status_text = _position_label(mover_eval_before)
    severity_text = _severity_label(eval_loss_cp)
    rank_text = _played_rank_text(critical)
    best_plan_text = _best_plan_text(critical, best_option, prompt_type)
    mistake_text = _mistake_text(critical, prompt_type, mover_eval_after, played_option)

    intro = (
        f"In {opening_text}, {critical.side_to_move} was {status_text} before the mistake."
        if critical.side_to_move
        else f"In {opening_text}, the position was {status_text} before the mistake."
    )

    swing_text = (
        f"The swing is about {critical.eval_loss_display or f'{int(eval_loss_cp)} cp'},"
        f" so this is a {severity_text} error."
    )

    pv_text = f" A useful engine line is {critical.best_pv_san}." if critical.best_pv_san else ""
    rank_suffix = f" {rank_text}" if rank_text else ""

    return f"{intro} {best_plan_text} {mistake_text} {swing_text}{rank_suffix}{pv_text}"


def build_puzzles(critical_positions: Iterable[CriticalPosition]) -> List[PuzzleRecord]:
    puzzles: List[PuzzleRecord] = []
    for idx, critical in enumerate(critical_positions, start=1):
        prompt_type = assign_prompt_type(critical)
        side_to_move = critical.side_to_move
        puzzles.append(
            PuzzleRecord(
                puzzle_id=f"puzzle_{idx:05d}",
                fen=critical.fen,
                side_to_move=side_to_move,
                move_number=critical.move_number,
                prompt=_prompt_text(prompt_type, side_to_move),
                prompt_type=prompt_type,
                recommended_focus=_recommended_focus(prompt_type),
                notes_placeholder="",
                played_move=critical.played_move,
                engine_best_move=critical.engine_best_move,
                eval_before_cp=critical.eval_before,
                eval_after_cp=critical.eval_after,
                eval_swing_cp=critical.eval_swing,
                is_mate_related=critical.mate_related,
                source_file=critical.source_file,
                game_index=critical.game_index,
                event=critical.event,
                site=critical.site,
                date=critical.date,
                white=critical.white,
                black=critical.black,
                result=critical.result,
                eco=critical.eco,
                opening=critical.opening,
                lichess_url=_lichess_analysis_url(critical.fen, critical.side_to_move),
                puzzle_prompt_type=prompt_type,
                best_move_uci=critical.engine_best_move_uci,
                best_move_san=critical.engine_best_move,
                played_move_uci=critical.played_move_uci,
                played_move_san=critical.played_move,
                best_eval=critical.eval_before,
                best_eval_display=critical.best_eval_display,
                played_eval=critical.eval_after,
                played_eval_display=critical.played_eval_display,
                eval_loss=critical.eval_swing,
                eval_loss_display=critical.eval_loss_display,
                best_pv=critical.best_pv_san,
                prompt_hint=_build_prompt_hint(critical, prompt_type),
                explanation=_build_explanation(critical, prompt_type),
                tags=_build_tags(critical, prompt_type),
                legal_move_options=list(critical.legal_move_options),
            )
        )
    return puzzles
