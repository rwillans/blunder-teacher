from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from .critical_analysis import CriticalPosition


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


def assign_prompt_type(critical: CriticalPosition) -> str:
    """Simple rule-based prompt selector for v1 puzzle export."""
    # Mate transitions are usually tactical danger moments.
    if critical.mate_related:
        return "Spot the danger"

    # Already under pressure before the move: emphasize defense.
    if critical.eval_before < -80:
        return "Defend accurately"

    # Not yet bad, but the played move allows a dangerous downturn.
    if critical.eval_after <= -100:
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
            )
        )
    return puzzles
