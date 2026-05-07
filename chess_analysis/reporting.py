from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from .puzzles import PuzzleRecord


def build_puzzle_payload(puzzles: list[PuzzleRecord]) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for puzzle in puzzles:
        payload.append(
            {
                "id": puzzle.puzzle_id,
                "fen": puzzle.fen,
                "side_to_move": puzzle.side_to_move,
                "move_number": puzzle.move_number,
                "prompt": puzzle.prompt,
                "puzzle_prompt_type": puzzle.puzzle_prompt_type or puzzle.prompt_type,
                "puzzle_theme": puzzle.puzzle_theme,
                "opening": puzzle.opening or "Unknown Opening",
                "recommended_focus": puzzle.recommended_focus,
                "event": puzzle.event,
                "site": puzzle.site,
                "date": puzzle.date,
                "white": puzzle.white,
                "black": puzzle.black,
                "result": puzzle.result,
                "source_file": puzzle.source_file,
                "game_index": puzzle.game_index,
                "eco": puzzle.eco,
                "lichess_url": puzzle.lichess_url,
                "best_move_uci": puzzle.best_move_uci,
                "best_move_san": puzzle.best_move_san,
                "played_move_uci": puzzle.played_move_uci,
                "played_move_san": puzzle.played_move_san,
                "best_eval": puzzle.best_eval,
                "best_eval_display": puzzle.best_eval_display,
                "played_eval": puzzle.played_eval,
                "played_eval_display": puzzle.played_eval_display,
                "eval_loss": puzzle.eval_loss,
                "eval_loss_display": puzzle.eval_loss_display,
                "best_pv": puzzle.best_pv,
                "prompt_hint": puzzle.prompt_hint,
                "explanation": puzzle.explanation,
                "tags": puzzle.tags,
                "legal_move_options": [asdict(option) for option in puzzle.legal_move_options],
            }
        )
    return payload


def _write_puzzle_payload_file(output_file: Path, puzzles: Iterable[PuzzleRecord]) -> Path:
    payload = build_puzzle_payload(list(puzzles))
    output_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    return output_file


def write_puzzles_json(output_dir: Path, puzzles: Iterable[PuzzleRecord]) -> Path:
    return _write_puzzle_payload_file(output_dir / "puzzles.json", puzzles)


def write_web_public_puzzles_json(project_root: Path, puzzles: Iterable[PuzzleRecord]) -> Path | None:
    web_dir = project_root / "web"
    if not web_dir.exists():
        return None

    public_dir = web_dir / "public"
    public_dir.mkdir(parents=True, exist_ok=True)
    return _write_puzzle_payload_file(public_dir / "puzzles.json", puzzles)
