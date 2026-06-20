from __future__ import annotations

import hashlib
import json
import chess
from dataclasses import dataclass, field
from typing import Iterable, List
from urllib.parse import quote

from .critical_analysis import CriticalPosition, LegalMoveOption

PROMPT_DELIVER_CHECKMATE = "Deliver checkmate"
PROMPT_AVOID_CHECKMATE = "Avoid checkmate"
PROMPT_DEFEND = "Defend accurately"
PROMPT_WIN_MATERIAL = "Win material"
PROMPT_EXPLOIT_TACTIC = "Exploit the tactic"
PROMPT_QUIET_RESOURCE = "Find the quiet resource"
PROMPT_PROMOTE = "Promote the pawn"
PROMPT_CONVERT_ADVANTAGE = "Convert the advantage"
PROMPT_EQUALISE = "Equalise"
PROMPT_BEST_CONTINUATION = "Find the best continuation"

MATE_THEMES = {"Checkmate", "Mate in 1", "Mate in 2", "Mate in 3", "Mate in 4", "Mate in 5 or more"}
TACTICAL_THEMES = {
    "Advanced pawn",
    "Attacking f2 or f7",
    "Back rank mate",
    "Capture the defender",
    "Defensive move",
    "Discovered attack",
    "Discovered check",
    "Double check",
    "Fork",
    "Hanging piece",
    "Kingside attack",
    "Pin",
    "Queenside attack",
    "Quiet move",
    "Sacrifice",
    "Skewer",
}
SPECIAL_MOVE_THEMES = {"Castling", "En passant rights", "Promotion", "Underpromotion"}
GOAL_THEMES = {"Equality", "Advantage", "Crushing"}
PHASE_THEMES = {
    "Opening",
    "Middlegame",
    "Endgame",
    "Rook endgame",
    "Bishop endgame",
    "Pawn endgame",
    "Knight endgame",
    "Queen endgame",
    "Queen and Rook",
}


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


@dataclass(frozen=True)
class ReplayedMove:
    board_before: chess.Board
    move: chess.Move
    board_after: chess.Board
    mover_color: bool
    ply_index: int


def _normalize_identity_value(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _normalized_game_identity(critical: CriticalPosition) -> dict[str, object]:
    if critical.game_id:
        return {"game_id": _normalize_identity_value(critical.game_id)}
    return {
        "event": _normalize_identity_value(critical.event),
        "site": _normalize_identity_value(critical.site),
        "date": _normalize_identity_value(critical.date),
        "white": _normalize_identity_value(critical.white),
        "black": _normalize_identity_value(critical.black),
        "result": _normalize_identity_value(critical.result),
        "source_file": _normalize_identity_value(critical.source_file),
        "game_index": int(critical.game_index or 0),
    }


def _ply_location(critical: CriticalPosition) -> dict[str, object]:
    try:
        board = chess.Board(critical.fen)
        fullmove_number = board.fullmove_number
        active_color = "white" if board.turn == chess.WHITE else "black"
        ply_index = max(0, (fullmove_number - 1) * 2 + (0 if board.turn == chess.WHITE else 1))
    except ValueError:
        fullmove_number = int(critical.move_number or 0)
        active_color = _normalize_identity_value(critical.side_to_move)
        ply_index = max(0, (fullmove_number - 1) * 2 + (0 if active_color == "white" else 1))

    return {
        "fullmove_number": fullmove_number,
        "active_color": active_color,
        "ply_index": ply_index,
        "played_move_uci": _normalize_identity_value(critical.played_move_uci),
    }


def stable_puzzle_id(critical: CriticalPosition) -> str:
    identity = {
        "game": _normalized_game_identity(critical),
        "fen": " ".join(critical.fen.strip().split()),
        "location": _ply_location(critical),
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"puzzle_{hashlib.sha256(encoded).hexdigest()[:12]}"


def _eval_for_side(eval_cp: float, side_to_move: str) -> float:
    return eval_cp if side_to_move.strip().lower() == "white" else -eval_cp


def assign_prompt_type(critical: CriticalPosition) -> str:
    """Rule-based instructional prompt selector for puzzle export."""
    return _prompt_type_for_themes(critical, assign_puzzle_themes(critical))


def _prompt_type_for_themes(critical: CriticalPosition, themes: list[str]) -> str:
    best_option = _find_best_option(critical)
    played_option = _find_played_option(critical)
    mover_eval_before = _eval_for_side(critical.eval_before, critical.side_to_move)
    mover_eval_after = (
        float(played_option.mover_eval_cp)
        if played_option is not None
        else _eval_for_side(critical.eval_after, critical.side_to_move)
    )

    if (
        best_option is not None
        and best_option.mover_mate is not None
        and best_option.mover_mate > 0
    ) or (critical.mate_related and mover_eval_before >= 100000):
        return PROMPT_DELIVER_CHECKMATE

    if (
        played_option is not None
        and played_option.mover_mate is not None
        and played_option.mover_mate < 0
    ) or (critical.mate_related and mover_eval_after <= -100000):
        return PROMPT_AVOID_CHECKMATE

    if "Defensive move" in themes or mover_eval_before < -80:
        return PROMPT_DEFEND

    if "Promotion" in themes or "Underpromotion" in themes:
        return PROMPT_PROMOTE

    if "Quiet move" in themes:
        return PROMPT_QUIET_RESOURCE

    if "Hanging piece" in themes or _best_move_wins_material(critical, best_option):
        return PROMPT_WIN_MATERIAL

    if any(theme in TACTICAL_THEMES - {"Defensive move", "Quiet move"} for theme in themes):
        return PROMPT_EXPLOIT_TACTIC

    if mover_eval_before >= 600:
        return PROMPT_CONVERT_ADVANTAGE

    if -80 <= mover_eval_before <= 80 and mover_eval_after <= -80:
        return PROMPT_EQUALISE

    return PROMPT_BEST_CONTINUATION


def _safe_board(fen: str) -> chess.Board | None:
    try:
        return chess.Board(fen)
    except ValueError:
        return None


def _mate_theme(best_option: LegalMoveOption | None) -> str | None:
    if best_option is None or best_option.mover_mate is None or best_option.mover_mate <= 0:
        return None
    if best_option.mover_mate == 1:
        return "Mate in 1"
    if best_option.mover_mate == 2:
        return "Mate in 2"
    if best_option.mover_mate == 3:
        return "Mate in 3"
    if best_option.mover_mate == 4:
        return "Mate in 4"
    return "Mate in 5 or more"


def assign_puzzle_theme(critical: CriticalPosition) -> str:
    return _primary_theme(assign_puzzle_themes(critical))


def assign_puzzle_themes(critical: CriticalPosition) -> list[str]:
    best_option = _find_best_option(critical)
    themes: list[str] = []

    mate_theme = _mate_theme(best_option)
    if mate_theme is not None:
        themes.append(mate_theme)
        themes.append("Checkmate")
    elif critical.mate_related:
        themes.append("Checkmate")

    themes.extend(_motif_tags(critical))
    themes.extend(_goal_tags(critical, best_option))
    themes.extend(_phase_tags(critical))

    ordered = _dedupe(themes) or ["Middlegame"]
    primary = _primary_theme(ordered)
    return [primary] + [theme for theme in ordered if theme != primary]


def _primary_theme(themes: list[str]) -> str:
    for theme_group in (MATE_THEMES, TACTICAL_THEMES, SPECIAL_MOVE_THEMES, GOAL_THEMES, PHASE_THEMES):
        for theme in themes:
            if theme in theme_group:
                return theme
    return themes[0] if themes else "Middlegame"


def _dedupe(tags: Iterable[str]) -> list[str]:
    deduped: list[str] = []
    for tag in tags:
        if tag and tag not in deduped:
            deduped.append(tag)
    return deduped


def _recommended_focus(prompt_type: str) -> str:
    if prompt_type == PROMPT_DELIVER_CHECKMATE:
        return "forcing mate"
    if prompt_type == PROMPT_AVOID_CHECKMATE:
        return "mating threats"
    if prompt_type == PROMPT_DEFEND:
        return "defence and damage control"
    if prompt_type == PROMPT_WIN_MATERIAL:
        return "loose pieces and tactics"
    if prompt_type == PROMPT_EXPLOIT_TACTIC:
        return "tactical motifs"
    if prompt_type == PROMPT_QUIET_RESOURCE:
        return "quiet resources"
    if prompt_type == PROMPT_PROMOTE:
        return "promotion tactics"
    if prompt_type == PROMPT_CONVERT_ADVANTAGE:
        return "conversion technique"
    if prompt_type == PROMPT_EQUALISE:
        return "equality and stability"
    if prompt_type == "Find the best move":
        return "candidate moves"
    if prompt_type == "Spot the danger":
        return "opponent threats"
    return "candidate moves"


def _prompt_text(prompt_type: str, side_to_move: str) -> str:
    if prompt_type == PROMPT_DELIVER_CHECKMATE:
        return f"{side_to_move} to move: Find the forcing mate."
    if prompt_type == PROMPT_AVOID_CHECKMATE:
        return f"{side_to_move} to move: Stop the mating threat."
    if prompt_type == PROMPT_DEFEND:
        return f"{side_to_move} to move: Defend accurately and limit the damage."
    if prompt_type == PROMPT_WIN_MATERIAL:
        return f"{side_to_move} to move: Win material with the right tactic."
    if prompt_type == PROMPT_EXPLOIT_TACTIC:
        return f"{side_to_move} to move: Exploit the tactical idea."
    if prompt_type == PROMPT_QUIET_RESOURCE:
        return f"{side_to_move} to move: Find the quiet resource."
    if prompt_type == PROMPT_PROMOTE:
        return f"{side_to_move} to move: Use the pawn breakthrough."
    if prompt_type == PROMPT_CONVERT_ADVANTAGE:
        return f"{side_to_move} to move: Convert the advantage cleanly."
    if prompt_type == PROMPT_EQUALISE:
        return f"{side_to_move} to move: Find the resource that holds equality."
    if prompt_type == "Find the best move":
        return f"{side_to_move} to move: Find the best move."
    if prompt_type == "Spot the danger":
        return f"{side_to_move} to move: Spot the danger and identify the critical threat."
    return f"{side_to_move} to move: Defend accurately and limit the damage."


def _lichess_analysis_url(fen: str, side_to_move: str) -> str:
    color = "white" if side_to_move.strip().lower() == "white" else "black"
    return f"https://lichess.org/analysis/{quote(fen, safe='/')}?color={color}"


def _build_tags(critical: CriticalPosition, prompt_type: str | None = None) -> list[str]:
    return assign_puzzle_themes(critical)


def _goal_tags(critical: CriticalPosition, best_option: LegalMoveOption | None) -> list[str]:
    mover_eval = _eval_for_side(critical.eval_before, critical.side_to_move)
    if best_option is not None and best_option.mover_mate is not None and best_option.mover_mate > 0:
        return ["Checkmate"]
    if mover_eval < -80:
        return ["Defensive move"]
    if mover_eval >= 600:
        return ["Crushing"]
    if mover_eval >= 200:
        return ["Advantage"]
    return ["Equality"]


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


def _special_move_tags(board: chess.Board, move: chess.Move) -> list[str]:
    tags: list[str] = []
    promotion_tag = _promotion_tag(move)
    if promotion_tag is not None:
        tags.append(promotion_tag)
    if board.is_castling(move):
        tags.append("Castling")
    if board.is_en_passant(move):
        tags.append("En passant rights")
    return tags


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


def _best_move_wins_material(critical: CriticalPosition, best_option: LegalMoveOption | None) -> bool:
    if best_option is None:
        return False
    board_before = _safe_board(critical.fen)
    board_after = _safe_board(best_option.resulting_fen)
    if board_before is None or board_after is None:
        return False
    mover_color = board_before.turn
    before_balance = _material_balance(board_before, mover_color)
    after_balance = _material_balance(board_after, mover_color)
    return after_balance >= before_balance + 1


def _best_move_sacrifices_material(critical: CriticalPosition, best_option: LegalMoveOption | None) -> bool:
    if best_option is None:
        return False
    board_before = _safe_board(critical.fen)
    board_after = _safe_board(best_option.resulting_fen)
    if board_before is None or board_after is None:
        return False
    mover_color = board_before.turn
    before_balance = _material_balance(board_before, mover_color)
    after_balance = _material_balance(board_after, mover_color)
    return after_balance <= before_balance - 1 and float(best_option.mover_eval_cp) >= -80


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


def _advanced_pawn_tag(board_after: chess.Board, move: chess.Move, mover_color: bool) -> bool:
    moved_piece = board_after.piece_at(move.to_square)
    if moved_piece is None or moved_piece.piece_type != chess.PAWN or moved_piece.color != mover_color:
        return False
    rank = chess.square_rank(move.to_square)
    if mover_color == chess.WHITE:
        return rank >= 5
    return rank <= 2


def _attacking_f2_or_f7_tag(board_after: chess.Board, move: chess.Move, mover_color: bool) -> bool:
    target_square = chess.F7 if mover_color == chess.WHITE else chess.F2
    moved_piece = board_after.piece_at(move.to_square)
    if moved_piece is None or moved_piece.color != mover_color:
        return False
    if move.to_square == target_square:
        return True
    target_piece = board_after.piece_at(target_square)
    return target_piece is not None and target_piece.color != mover_color and target_square in board_after.attacks(move.to_square)


def _pin_tag(board_before: chess.Board, board_after: chess.Board, mover_color: bool) -> bool:
    enemy_color = not mover_color
    for square, piece in board_after.piece_map().items():
        if (
            piece.color == enemy_color
            and piece.piece_type != chess.KING
            and board_after.is_pinned(enemy_color, square)
            and not board_before.is_pinned(enemy_color, square)
        ):
            return True
    return False


def _ray_step(from_square: chess.Square, to_square: chess.Square) -> int | None:
    from_file = chess.square_file(from_square)
    from_rank = chess.square_rank(from_square)
    to_file = chess.square_file(to_square)
    to_rank = chess.square_rank(to_square)
    file_delta = to_file - from_file
    rank_delta = to_rank - from_rank

    if file_delta == 0 and rank_delta != 0:
        return 8 if rank_delta > 0 else -8
    if rank_delta == 0 and file_delta != 0:
        return 1 if file_delta > 0 else -1
    if abs(file_delta) == abs(rank_delta) and file_delta != 0:
        if file_delta > 0 and rank_delta > 0:
            return 9
        if file_delta > 0 and rank_delta < 0:
            return -7
        if file_delta < 0 and rank_delta > 0:
            return 7
        return -9
    return None


def _step_keeps_ray(previous_square: chess.Square, next_square: chess.Square, step: int) -> bool:
    previous_file = chess.square_file(previous_square)
    next_file = chess.square_file(next_square)
    if step in (1, -1):
        return chess.square_rank(previous_square) == chess.square_rank(next_square)
    if step in (7, -7, 9, -9):
        return abs(previous_file - next_file) == 1
    return True


def _skewer_tag(board_after: chess.Board, move: chess.Move, mover_color: bool) -> bool:
    moved_piece = board_after.piece_at(move.to_square)
    enemy_king_square = board_after.king(not mover_color)
    if (
        moved_piece is None
        or moved_piece.piece_type not in (chess.BISHOP, chess.ROOK, chess.QUEEN)
        or enemy_king_square is None
        or not board_after.is_check()
        or enemy_king_square not in board_after.attacks(move.to_square)
    ):
        return False

    step = _ray_step(move.to_square, enemy_king_square)
    if step is None:
        return False

    previous_square = enemy_king_square
    square = enemy_king_square + step
    while 0 <= square < 64 and _step_keeps_ray(previous_square, square, step):
        piece = board_after.piece_at(square)
        if piece is not None:
            return piece.color != mover_color and piece.piece_type not in (chess.KING, chess.PAWN)
        previous_square = square
        square += step
    return False


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


def _discovered_attack(board: chess.Board, move: chess.Move) -> bool:
    mover_color = board.turn
    board_after = board.copy(stack=False)
    board_after.push(move)
    source = move.from_square
    for target_square, piece in board_after.piece_map().items():
        if piece.color == mover_color or piece.piece_type == chess.KING:
            continue
        for attacker_square in board_after.attackers(mover_color, target_square):
            if attacker_square == move.to_square:
                continue
            attacker = board_after.piece_at(attacker_square)
            if attacker is None or attacker.piece_type not in (chess.BISHOP, chess.ROOK, chess.QUEEN):
                continue
            if source in chess.SquareSet.between(attacker_square, target_square):
                return True
    return False


def _double_check(board_after: chess.Board, mover_color: bool) -> bool:
    enemy_king_square = board_after.king(not mover_color)
    if enemy_king_square is None or not board_after.is_check():
        return False
    return len(board_after.attackers(mover_color, enemy_king_square)) >= 2


def _back_rank_mate(board_after: chess.Board, mated_color: bool) -> bool:
    if not board_after.is_checkmate():
        return False
    king_square = board_after.king(mated_color)
    if king_square is None:
        return False
    king_rank = chess.square_rank(king_square)
    return (mated_color == chess.WHITE and king_rank == 0) or (mated_color == chess.BLACK and king_rank == 7)


def _king_area_attack_tag(board_after: chess.Board, mover_color: bool) -> str | None:
    enemy_king_square = board_after.king(not mover_color)
    if enemy_king_square is None or not board_after.is_check():
        return None
    file_index = chess.square_file(enemy_king_square)
    if file_index >= 5:
        return "Kingside attack"
    if file_index <= 2:
        return "Queenside attack"
    return None


def _quiet_move_tag(board: chess.Board, board_after: chess.Board, move: chess.Move, critical: CriticalPosition) -> bool:
    if (
        board.is_capture(move)
        or board.is_castling(move)
        or move.promotion is not None
        or board_after.is_check()
    ):
        return False
    played_option = _find_played_option(critical)
    eval_loss_cp = float(played_option.eval_loss_cp) if played_option is not None else abs(float(critical.eval_swing))
    return eval_loss_cp >= 250 or critical.mate_related


def _replay_pv_uci(fen: str, pv_uci: list[str]) -> list[ReplayedMove]:
    board = _safe_board(fen)
    if board is None:
        return []

    replayed: list[ReplayedMove] = []
    for ply_index, move_uci in enumerate(pv_uci, start=1):
        try:
            move = chess.Move.from_uci(move_uci)
        except ValueError:
            break
        if move not in board.legal_moves:
            break

        board_before = board.copy(stack=False)
        mover_color = board.turn
        board.push(move)
        replayed.append(
            ReplayedMove(
                board_before=board_before,
                move=move,
                board_after=board.copy(stack=False),
                mover_color=mover_color,
                ply_index=ply_index,
            )
        )
    return replayed


def _best_line_moves(critical: CriticalPosition, best_option: LegalMoveOption | None) -> list[ReplayedMove]:
    if best_option is not None and best_option.pv_uci:
        return _replay_pv_uci(critical.fen, best_option.pv_uci)
    if not critical.engine_best_move_uci:
        return []
    return _replay_pv_uci(critical.fen, [critical.engine_best_move_uci])


def _capture_the_defender(line_moves: list[ReplayedMove], original_color: bool) -> bool:
    if not line_moves:
        return False

    first_move = line_moves[0]
    if first_move.mover_color != original_color or not first_move.board_before.is_capture(first_move.move):
        return False

    captured_piece = first_move.board_before.piece_at(first_move.move.to_square)
    if captured_piece is None or captured_piece.color == original_color:
        return False

    defended_targets: set[chess.Square] = set()
    for square, piece in first_move.board_before.piece_map().items():
        if piece.color == original_color or piece.piece_type in (chess.KING, chess.PAWN):
            continue
        if square in first_move.board_before.attacks(first_move.move.to_square):
            defended_targets.add(square)

    if not defended_targets:
        return False

    for line_move in line_moves[1:]:
        if line_move.mover_color != original_color or not line_move.board_before.is_capture(line_move.move):
            continue
        if line_move.move.to_square in defended_targets:
            return True
    return False


def _motif_tags_for_replayed_move(
    line_move: ReplayedMove,
    critical: CriticalPosition,
    best_option: LegalMoveOption | None,
    original_color: bool,
) -> list[str]:
    board = line_move.board_before
    move = line_move.move
    board_after = line_move.board_after
    tags: list[str] = []

    tags.extend(_special_move_tags(board, move))
    if _capture_hanging_piece(board, move):
        tags.append("Hanging piece")
    if _discovered_attack(board, move):
        tags.append("Discovered attack")
    if _discovered_check(board, move):
        tags.append("Discovered check")

    if board_after.is_checkmate():
        tags.append("Checkmate")
        if _back_rank_mate(board_after, not original_color):
            tags.append("Back rank mate")

    enemy_king_square = board_after.king(not original_color)
    if enemy_king_square is not None and board_after.is_check() and board_after.attackers(original_color, enemy_king_square):
        if "Checkmate" not in tags:
            tags.append("Exposed king")
    if _double_check(board_after, original_color):
        tags.append("Double check")
    if _fork_tag(board_after, move, original_color):
        tags.append("Fork")
    if _pin_tag(board, board_after, original_color):
        tags.append("Pin")
    if _skewer_tag(board_after, move, original_color):
        tags.append("Skewer")
    if _advanced_pawn_tag(board_after, move, original_color):
        tags.append("Advanced pawn")
    if _attacking_f2_or_f7_tag(board_after, move, original_color):
        tags.append("Attacking f2 or f7")

    king_attack_tag = _king_area_attack_tag(board_after, original_color)
    if king_attack_tag is not None:
        tags.append(king_attack_tag)
    if line_move.ply_index == 1 and _best_move_sacrifices_material(critical, best_option):
        tags.append("Sacrifice")
    if line_move.ply_index == 1 and _quiet_move_tag(board, board_after, move, critical):
        tags.append("Quiet move")
    return tags


def _motif_tags(critical: CriticalPosition) -> list[str]:
    best_option = _find_best_option(critical)
    line_moves = _best_line_moves(critical, best_option)
    if not line_moves:
        return []

    original_color = line_moves[0].mover_color
    tags: list[str] = []

    if best_option is not None and best_option.mover_mate is not None and best_option.mover_mate > 0:
        tags.append("Checkmate")
    if _capture_the_defender(line_moves, original_color):
        tags.append("Capture the defender")

    for line_move in line_moves:
        if line_move.mover_color != original_color:
            continue
        tags.extend(_motif_tags_for_replayed_move(line_move, critical, best_option, original_color))

    return _dedupe(tags)


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

    if best_option is not None and best_option.mover_mate is not None and best_option.mover_mate > 0:
        return f"{best_move} was a forcing move: it keeps a mating attack with {best_option.mover_eval_display}."

    if prompt_type == PROMPT_DEFEND:
        return f"{best_move} was the cleanest defensive try, keeping the position around {best_eval}."
    if prompt_type == PROMPT_AVOID_CHECKMATE:
        return f"{best_move} was the critical defensive move, holding off the mating attack at about {best_eval}."
    if prompt_type == PROMPT_WIN_MATERIAL:
        return f"{best_move} was the material-winning resource, keeping the position around {best_eval}."
    if prompt_type == PROMPT_EXPLOIT_TACTIC:
        return f"{best_move} was the tactical resource, holding the line at about {best_eval}."
    if prompt_type == PROMPT_QUIET_RESOURCE:
        return f"{best_move} was the quiet resource, preserving roughly {best_eval}."
    if prompt_type == PROMPT_PROMOTE:
        return f"{best_move} was the pawn breakthrough, keeping the position around {best_eval}."
    if prompt_type == PROMPT_CONVERT_ADVANTAGE:
        return f"{best_move} was the clean conversion, preserving roughly {best_eval}."
    if prompt_type == PROMPT_EQUALISE:
        return f"{best_move} was the balancing resource, keeping the position around {best_eval}."
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

    if prompt_type == PROMPT_DEFEND:
        return f"{played_move} failed to stabilise the position and left the side to move on {played_eval}."
    if prompt_type == PROMPT_AVOID_CHECKMATE:
        return f"{played_move} misses the defensive resource and leaves the side to move on {played_eval}."
    if prompt_type == PROMPT_WIN_MATERIAL:
        return f"{played_move} misses the material-winning tactic and leaves the position on {played_eval}."
    if prompt_type == PROMPT_EXPLOIT_TACTIC:
        return f"{played_move} misses the tactical point and leaves the position on {played_eval}."
    if prompt_type == PROMPT_QUIET_RESOURCE:
        return f"{played_move} misses the quiet resource and leaves the position on {played_eval}."
    if prompt_type == PROMPT_PROMOTE:
        return f"{played_move} misses the pawn resource and leaves the position on {played_eval}."
    if prompt_type == PROMPT_CONVERT_ADVANTAGE:
        return f"{played_move} lets the advantage slip and leaves the position on {played_eval}."
    if prompt_type == PROMPT_EQUALISE:
        return f"{played_move} misses the chance to hold equality and leaves the position on {played_eval}."
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

    if prompt_type == PROMPT_DEFEND:
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
    for critical in critical_positions:
        tags = assign_puzzle_themes(critical)
        prompt_type = _prompt_type_for_themes(critical, tags)
        side_to_move = critical.side_to_move
        puzzles.append(
            PuzzleRecord(
                puzzle_id=stable_puzzle_id(critical),
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
                puzzle_theme=tags[0] if tags else "",
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
                tags=tags,
                legal_move_options=list(critical.legal_move_options),
            )
        )
    return puzzles
