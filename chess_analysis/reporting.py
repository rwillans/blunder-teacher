from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Iterable

from .critical_analysis import CriticalPosition
from .engine_check import EngineCheckResult
from .pgn_parser import GameRecord
from .puzzles import PuzzleRecord


def write_games_summary_csv(output_dir: Path, records: Iterable[GameRecord]) -> Path:
    output_file = output_dir / "games_summary.csv"
    rows = list(records)

    with output_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "source_file",
                "game_index",
                "event",
                "site",
                "date",
                "white",
                "black",
                "result",
                "eco",
                "opening",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.source_file,
                    row.game_index,
                    row.event,
                    row.site,
                    row.date,
                    row.white,
                    row.black,
                    row.result,
                    row.eco,
                    row.opening,
                ]
            )

    return output_file


def write_critical_positions_csv(output_dir: Path, critical_positions: Iterable[CriticalPosition]) -> Path:
    output_file = output_dir / "critical_positions.csv"
    rows = list(critical_positions)

    with output_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "source_file",
                "game_index",
                "event",
                "site",
                "date",
                "white",
                "black",
                "result",
                "move_number",
                "side_to_move",
                "fen",
                "played_move",
                "engine_best_move",
                "eval_before",
                "eval_after",
                "eval_swing",
                "mate_related",
                "eco",
                "opening",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.source_file,
                    row.game_index,
                    row.event,
                    row.site,
                    row.date,
                    row.white,
                    row.black,
                    row.result,
                    row.move_number,
                    row.side_to_move,
                    row.fen,
                    row.played_move,
                    row.engine_best_move,
                    row.eval_before,
                    row.eval_after,
                    row.eval_swing,
                    row.mate_related,
                    row.eco,
                    row.opening,
                ]
            )

    return output_file


def write_puzzles_csv(output_dir: Path, puzzles: Iterable[PuzzleRecord]) -> Path:
    output_file = output_dir / "puzzles.csv"
    rows = list(puzzles)

    with output_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "puzzle_id",
                "fen",
                "side_to_move",
                "move_number",
                "prompt",
                "prompt_type",
                "recommended_focus",
                "notes_placeholder",
                "played_move",
                "engine_best_move",
                "eval_before_cp",
                "eval_after_cp",
                "eval_swing_cp",
                "is_mate_related",
                "source_file",
                "game_index",
                "event",
                "site",
                "date",
                "white",
                "black",
                "result",
                "eco",
                "opening",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.puzzle_id,
                    row.fen,
                    row.side_to_move,
                    row.move_number,
                    row.prompt,
                    row.prompt_type,
                    row.recommended_focus,
                    row.notes_placeholder,
                    row.played_move,
                    row.engine_best_move,
                    row.eval_before_cp,
                    row.eval_after_cp,
                    row.eval_swing_cp,
                    row.is_mate_related,
                    row.source_file,
                    row.game_index,
                    row.event,
                    row.site,
                    row.date,
                    row.white,
                    row.black,
                    row.result,
                    row.eco,
                    row.opening,
                ]
            )

    return output_file


def write_summary_report_md(
    output_dir: Path,
    records: Iterable[GameRecord],
    critical_positions: Iterable[CriticalPosition],
    puzzles: Iterable[PuzzleRecord],
    engine_result: EngineCheckResult,
) -> Path:
    output_file = output_dir / "summary_report.md"
    rows = list(records)
    critical = list(critical_positions)
    puzzle_rows = list(puzzles)

    players = sorted({name for r in rows for name in (r.white, r.black) if name})
    results = Counter(r.result for r in rows if r.result)
    openings = sorted({r.opening for r in rows if r.opening})
    missing_opening_or_eco = sum(1 for r in rows if not r.opening or not r.eco)

    critical_by_game = Counter((c.source_file, c.game_index) for c in critical)
    top_games = sorted(critical_by_game.items(), key=lambda item: item[1], reverse=True)[:5]
    move_hotspots = Counter(c.move_number for c in critical)
    top_moves = sorted(move_hotspots.items(), key=lambda item: item[1], reverse=True)[:10]

    mate_related_count = sum(1 for c in critical if c.mate_related)
    non_mate_swings = [c.eval_swing for c in critical if not c.mate_related]
    avg_non_mate_swing = mean(non_mate_swings) if non_mate_swings else 0.0
    max_non_mate_swing = max(non_mate_swings) if non_mate_swings else 0.0

    puzzle_prompt_counts = Counter(p.prompt_type for p in puzzle_rows)
    mate_related_puzzles = sum(1 for p in puzzle_rows if p.is_mate_related)

    lines = [
        "# Chess Analysis Summary Report",
        "",
        f"- Total number of games processed: **{len(rows)}**",
        f"- Number of critical moments found: **{len(critical)}**",
        f"- Number of mate-related critical moments: **{mate_related_count}**",
        f"- Number of puzzles exported: **{len(puzzle_rows)}**",
        f"- Number of mate-related puzzles: **{mate_related_puzzles}**",
        f"- Stockfish analysis succeeded: **{'Yes' if engine_result.success else 'No'}**",
        f"- Stockfish detail: `{engine_result.detail}`",
        f"- Games with missing Opening or ECO tags: **{missing_opening_or_eco}**",
        "",
        "## Players encountered",
    ]
    lines.extend([f"- {player}" for player in players] or ["- None"])

    lines.append("")
    lines.append("## Results summary")
    if results:
        for result, count in sorted(results.items()):
            lines.append(f"- {result}: {count}")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("## Openings encountered (where present)")
    lines.extend([f"- {opening}" for opening in openings] or ["- None"])

    lines.append("")
    lines.append("## Games with the most critical moments")
    if top_games:
        for (source_file, game_index), count in top_games:
            lines.append(f"- {source_file} (game {game_index}): {count}")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("## Move numbers where critical moments most often occurred")
    if top_moves:
        for move_number, count in top_moves:
            lines.append(f"- Move {move_number}: {count}")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("## Eval swing stats (non-mate critical moments)")
    lines.append(f"- Average centipawn swing (non-mate): **{avg_non_mate_swing:.2f} cp**")
    lines.append(f"- Maximum centipawn swing (non-mate): **{max_non_mate_swing:.2f} cp**")

    lines.append("")
    lines.append("## Puzzle counts by prompt type")
    if puzzle_prompt_counts:
        for prompt_type, count in sorted(puzzle_prompt_counts.items()):
            lines.append(f"- {prompt_type}: {count}")
    else:
        lines.append("- None")

    output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_file
