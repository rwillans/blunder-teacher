from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Iterable

from .engine_check import EngineCheckResult
from .pgn_parser import GameRecord


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


def write_summary_report_md(
    output_dir: Path, records: Iterable[GameRecord], engine_result: EngineCheckResult
) -> Path:
    output_file = output_dir / "summary_report.md"
    rows = list(records)

    players = sorted({name for r in rows for name in (r.white, r.black) if name})
    results = Counter(r.result for r in rows if r.result)
    openings = sorted({r.opening for r in rows if r.opening})

    missing_opening_or_eco = sum(1 for r in rows if not r.opening or not r.eco)

    lines = [
        "# Chess Analysis Summary Report",
        "",
        f"- Total number of games processed: **{len(rows)}**",
        f"- Stockfish analysis succeeded: **{'Yes' if engine_result.success else 'No'}**",
        f"- Stockfish detail: `{engine_result.detail}`",
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
    lines.append(f"- Games with missing Opening or ECO tags: **{missing_opening_or_eco}**")

    output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_file
