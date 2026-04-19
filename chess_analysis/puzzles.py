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
                explanation=_build_explanation(critical, prompt_type),
                tags=_build_tags(critical, prompt_type),
                legal_move_options=list(critical.legal_move_options),
            )
        )
    return puzzles
