from __future__ import annotations

import math
from collections import defaultdict
from typing import Iterable

from .puzzles import PuzzleRecord


def _eval_loss_cp(puzzle: PuzzleRecord) -> float:
    return max(0.0, float(puzzle.eval_loss or 0.0))


def _format_cp(value: float) -> str:
    if value >= 100000:
        return "Mate swing"
    return f"{int(round(value))} cp"


def _severity(value: float) -> str:
    if value >= 100000:
        return "Mate swing"
    if value >= 300:
        return "Major error"
    if value >= 120:
        return "Serious error"
    if value >= 50:
        return "Notable error"
    return "Small error"


def _move_number_bucket(move_number: int) -> str:
    if move_number <= 10:
        return "Opening"
    if move_number <= 20:
        return "Early middlegame"
    if move_number <= 35:
        return "Middlegame"
    return "Endgame"


def _phase(tags: list[str]) -> str:
    if "Endgame" in tags or any(tag.endswith("endgame") for tag in tags):
        return "Endgame"
    if "Opening" in tags:
        return "Opening"
    return "Middlegame"


def _example(puzzle: PuzzleRecord) -> dict[str, object]:
    return {
        "id": puzzle.puzzle_id,
        "prompt": puzzle.prompt,
        "opening": puzzle.opening or "Unknown Opening",
        "primary_theme": puzzle.puzzle_theme,
        "side_to_move": puzzle.side_to_move,
        "move_number": puzzle.move_number,
        "eval_loss": _eval_loss_cp(puzzle),
        "eval_loss_display": puzzle.eval_loss_display or _format_cp(_eval_loss_cp(puzzle)),
        "lichess_url": puzzle.lichess_url,
    }


def _group_values(puzzle: PuzzleRecord) -> Iterable[tuple[str, str]]:
    tags = list(dict.fromkeys(puzzle.tags or []))
    for tag in tags:
        yield "theme", tag
    if puzzle.puzzle_theme:
        yield "primary_theme", puzzle.puzzle_theme
    if puzzle.opening:
        yield "opening", puzzle.opening
    if puzzle.side_to_move:
        yield "side_to_move", puzzle.side_to_move
    if puzzle.puzzle_prompt_type or puzzle.prompt_type:
        yield "prompt_type", puzzle.puzzle_prompt_type or puzzle.prompt_type
    yield "move_number_bucket", _move_number_bucket(int(puzzle.move_number or 0))
    yield "eval_loss_severity", _severity(_eval_loss_cp(puzzle))
    yield "phase", _phase(tags)


def build_weakness_payload(puzzles: list[PuzzleRecord]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[PuzzleRecord]] = defaultdict(list)
    latest_overall = max((puzzle.date for puzzle in puzzles if puzzle.date), default="")

    for puzzle in puzzles:
        for group_key in _group_values(puzzle):
            grouped[group_key].append(puzzle)

    payload: list[dict[str, object]] = []
    for (group_type, label), group_puzzles in grouped.items():
        losses = [_eval_loss_cp(puzzle) for puzzle in group_puzzles]
        average_loss = sum(losses) / len(losses)
        max_loss = max(losses)
        latest_seen = max((puzzle.date for puzzle in group_puzzles if puzzle.date), default="")
        recency_multiplier = 1.25 if latest_seen and latest_seen == latest_overall else 1.0
        weakness_score = len(group_puzzles) * math.log1p(average_loss) * recency_multiplier
        examples = sorted(group_puzzles, key=_eval_loss_cp, reverse=True)[:3]

        payload.append(
            {
                "group_type": group_type,
                "label": label,
                "count": len(group_puzzles),
                "average_eval_loss": round(average_loss, 1),
                "average_eval_loss_display": _format_cp(average_loss),
                "max_eval_loss": max_loss,
                "max_eval_loss_display": _format_cp(max_loss),
                "mate_loss_count": sum(1 for loss in losses if loss >= 100000),
                "latest_seen": latest_seen,
                "recency_multiplier": recency_multiplier,
                "weakness_score": round(weakness_score, 2),
                "puzzle_ids": [puzzle.puzzle_id for puzzle in group_puzzles],
                "examples": [_example(puzzle) for puzzle in examples],
            }
        )

    return sorted(
        payload,
        key=lambda item: (
            -float(item["weakness_score"]),
            -int(item["count"]),
            str(item["group_type"]),
            str(item["label"]),
        ),
    )
