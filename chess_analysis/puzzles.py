from __future__ import annotations

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
    tags = [prompt_type, critical.side_to_move]
    if critical.opening:
        tags.append(critical.opening)
    if critical.mate_related:
        tags.append("mate-related")
    return tags


def _build_explanation(critical: CriticalPosition, prompt_type: str) -> str:
    if prompt_type == "Find the best move":
        lead = "The position still offered a stronger continuation than the game move."
    elif prompt_type == "Spot the danger":
        lead = "The game move missed a critical threat and let the evaluation slide."
    else:
        lead = "This position called for precise defence, and the game move made the position harder to hold."

    opening_text = critical.opening or "this line"
    return (
        f"In {opening_text}, {critical.engine_best_move or 'the engine suggestion'} kept the position at "
        f"{critical.best_eval_display or f'{critical.eval_before / 100:+.2f}'}, while "
        f"{critical.played_move or 'the played move'} dropped it to "
        f"{critical.played_eval_display or f'{critical.eval_after / 100:+.2f}'}. "
        f"That costs about {critical.eval_loss_display or f'{int(critical.eval_swing)} cp'}. "
        f"{lead}"
    )


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
                explanation=_build_explanation(critical, prompt_type),
                tags=_build_tags(critical, prompt_type),
                legal_move_options=list(critical.legal_move_options),
            )
        )
    return puzzles
