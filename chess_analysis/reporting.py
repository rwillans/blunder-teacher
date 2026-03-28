from __future__ import annotations

import csv
from collections import Counter
from html import escape
from pathlib import Path
from statistics import mean
from typing import Iterable
from urllib.parse import quote

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


def _lichess_analysis_url(fen: str, side_to_move: str) -> str:
    color = "white" if side_to_move.strip().lower() == "white" else "black"
    fen_path = quote(fen, safe="/")
    return f"https://lichess.org/analysis/{fen_path}?color={color}"


def write_puzzle_report_html(
    output_dir: Path,
    puzzles: Iterable[PuzzleRecord],
    input_path: str,
    player_filter: str | None,
    player_mistakes_only: bool,
) -> Path:
    output_file = output_dir / "puzzles.html"
    puzzle_rows = list(puzzles)

    grouped: dict[str, dict[str, list[PuzzleRecord]]] = {}
    for puzzle in puzzle_rows:
        prompt_group = grouped.setdefault(puzzle.prompt_type, {})
        opening_group = prompt_group.setdefault(puzzle.opening or "Unknown Opening", [])
        opening_group.append(puzzle)

    summary_bits = [
        f"<strong>{len(puzzle_rows)}</strong> puzzle(s)",
        f"Input: <code>{escape(input_path)}</code>",
        f"Player filter: <strong>{escape(player_filter or 'None')}</strong>",
        "Mistakes-only: <strong>{}</strong>".format("Yes" if player_mistakes_only else "No"),
    ]

    sections: list[str] = []
    for prompt_type in sorted(grouped):
        prompt_sections: list[str] = []
        for opening in sorted(grouped[prompt_type]):
            cards: list[str] = []
            for puzzle in grouped[prompt_type][opening]:
                description = (
                    f"{puzzle.event or 'Unknown event'} | {puzzle.date or 'Unknown date'} | "
                    f"{puzzle.white or 'White'} vs {puzzle.black or 'Black'} | "
                    f"Move {puzzle.move_number}: {puzzle.played_move}"
                )
                best_move_id = f"{puzzle.puzzle_id}-best-move"
                cards.append(
                    f"""
                    <article class="puzzle-card">
                      <div class="card-header">
                        <div>
                          <p class="eyebrow">{escape(puzzle.puzzle_id)}</p>
                          <h4>{escape(puzzle.prompt)}</h4>
                        </div>
                        <span class="badge">{escape(puzzle.side_to_move)} to move</span>
                      </div>
                      <p class="description">{escape(description)}</p>
                      <dl class="meta-grid">
                        <div>
                          <dt>Opening</dt>
                          <dd>{escape(puzzle.opening or 'Unknown Opening')}</dd>
                        </div>
                        <div>
                          <dt>Focus</dt>
                          <dd>{escape(puzzle.recommended_focus)}</dd>
                        </div>
                        <div>
                          <dt>FEN</dt>
                          <dd><code>{escape(puzzle.fen)}</code></dd>
                        </div>
                        <div>
                          <dt>Lichess</dt>
                          <dd><a href="{escape(_lichess_analysis_url(puzzle.fen, puzzle.side_to_move))}" target="_blank" rel="noreferrer">Open position on Lichess</a></dd>
                        </div>
                      </dl>
                      <div class="reveal-block">
                        <button type="button" class="reveal-button" data-target="{escape(best_move_id)}" aria-controls="{escape(best_move_id)}" aria-expanded="false">
                          Reveal best engine move
                        </button>
                        <p id="{escape(best_move_id)}" class="best-move" hidden>
                          Best engine move: <strong>{escape(puzzle.engine_best_move or 'Unavailable')}</strong>
                        </p>
                      </div>
                    </article>
                    """
                )

            prompt_sections.append(
                f"""
                <section class="opening-group">
                  <div class="group-heading">
                    <h3>{escape(opening)}</h3>
                    <span>{len(grouped[prompt_type][opening])} puzzle(s)</span>
                  </div>
                  <div class="puzzle-grid">
                    {''.join(cards)}
                  </div>
                </section>
                """
            )

        sections.append(
            f"""
            <section class="prompt-group">
              <div class="prompt-header">
                <h2>{escape(prompt_type)}</h2>
                <span>{sum(len(items) for items in grouped[prompt_type].values())} puzzle(s)</span>
              </div>
              {''.join(prompt_sections)}
            </section>
            """
        )

    body = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Blunder Teacher v5 Puzzle Report</title>
    <style>
      :root {{
        --bg: #f4efe6;
        --panel: #fffaf2;
        --panel-strong: #fff;
        --ink: #1f1a16;
        --muted: #6d6258;
        --accent: #155eef;
        --accent-soft: #dce8ff;
        --border: #d8ccbe;
        --shadow: 0 14px 34px rgba(45, 33, 20, 0.08);
      }}

      * {{
        box-sizing: border-box;
      }}

      body {{
        margin: 0;
        font-family: Georgia, "Times New Roman", serif;
        color: var(--ink);
        background:
          radial-gradient(circle at top left, rgba(21, 94, 239, 0.12), transparent 28%),
          linear-gradient(180deg, #fbf8f2 0%, var(--bg) 100%);
      }}

      main {{
        width: min(1180px, calc(100vw - 32px));
        margin: 0 auto;
        padding: 32px 0 48px;
      }}

      .hero {{
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.94), rgba(250, 242, 230, 0.92));
        border: 1px solid var(--border);
        border-radius: 24px;
        box-shadow: var(--shadow);
        padding: 28px;
        margin-bottom: 28px;
      }}

      .hero h1,
      .prompt-header h2,
      .group-heading h3,
      .card-header h4 {{
        margin: 0;
        font-family: "Palatino Linotype", Palatino, serif;
      }}

      .hero p {{
        margin: 12px 0 0;
        color: var(--muted);
        line-height: 1.6;
      }}

      .summary-strip {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 18px;
      }}

      .summary-strip span,
      .badge,
      .prompt-header span,
      .group-heading span {{
        background: var(--accent-soft);
        color: var(--accent);
        border-radius: 999px;
        padding: 8px 12px;
        font-size: 0.95rem;
      }}

      .prompt-group,
      .opening-group {{
        margin-bottom: 24px;
      }}

      .prompt-header,
      .group-heading,
      .card-header {{
        display: flex;
        justify-content: space-between;
        gap: 12px;
        align-items: flex-start;
      }}

      .opening-group {{
        background: rgba(255, 255, 255, 0.72);
        border: 1px solid rgba(216, 204, 190, 0.9);
        border-radius: 22px;
        padding: 20px;
        box-shadow: var(--shadow);
      }}

      .puzzle-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 16px;
        margin-top: 16px;
      }}

      .puzzle-card {{
        background: var(--panel-strong);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 18px;
      }}

      .eyebrow {{
        margin: 0 0 6px;
        color: var(--muted);
        font-size: 0.8rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }}

      .description {{
        margin: 14px 0;
        line-height: 1.6;
      }}

      .meta-grid {{
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 14px;
        margin: 0;
      }}

      .meta-grid div {{
        background: var(--panel);
        border-radius: 14px;
        padding: 12px;
      }}

      .meta-grid dt {{
        font-size: 0.8rem;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
      }}

      .meta-grid dd {{
        margin: 0;
        line-height: 1.5;
        word-break: break-word;
      }}

      .meta-grid code,
      .summary-strip code {{
        font-family: "Cascadia Code", Consolas, monospace;
        font-size: 0.9rem;
      }}

      .reveal-block {{
        margin-top: 16px;
      }}

      .reveal-button {{
        appearance: none;
        border: 0;
        border-radius: 999px;
        background: var(--accent);
        color: white;
        font: inherit;
        padding: 10px 16px;
        cursor: pointer;
      }}

      .reveal-button:hover,
      .reveal-button:focus-visible {{
        background: #0f4bcc;
      }}

      .best-move {{
        margin: 12px 0 0;
        padding: 12px 14px;
        border-left: 4px solid var(--accent);
        background: #eef4ff;
        border-radius: 0 12px 12px 0;
      }}

      .empty-state {{
        background: rgba(255, 255, 255, 0.82);
        border: 1px dashed var(--border);
        border-radius: 18px;
        padding: 24px;
        text-align: center;
        color: var(--muted);
      }}

      @media (max-width: 720px) {{
        main {{
          width: min(100vw - 18px, 100%);
          padding-top: 18px;
        }}

        .hero,
        .opening-group,
        .puzzle-card {{
          padding: 16px;
        }}

        .meta-grid {{
          grid-template-columns: 1fr;
        }}

        .prompt-header,
        .group-heading,
        .card-header {{
          flex-direction: column;
        }}
      }}
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <h1>Blunder Teacher v5 Puzzle Report</h1>
        <p>Puzzles are grouped first by prompt type and then by opening, so it is easier to review similar training moments together.</p>
        <p>Lichess links open the position directly. Engine visibility on Lichess is controlled there, so this report cannot reliably force it off by URL.</p>
        <div class="summary-strip">
          {''.join(f'<span>{bit}</span>' for bit in summary_bits)}
        </div>
      </section>
      {''.join(sections) if sections else '<section class="empty-state"><p>No puzzles were generated for this run.</p></section>'}
    </main>
    <script>
      for (const button of document.querySelectorAll('.reveal-button')) {{
        button.addEventListener('click', () => {{
          const target = document.getElementById(button.dataset.target);
          if (!target) return;
          const isHidden = target.hasAttribute('hidden');
          if (isHidden) {{
            target.removeAttribute('hidden');
            button.textContent = 'Hide best engine move';
            button.setAttribute('aria-expanded', 'true');
          }} else {{
            target.setAttribute('hidden', '');
            button.textContent = 'Reveal best engine move';
            button.setAttribute('aria-expanded', 'false');
          }}
        }});
      }}
    </script>
  </body>
</html>
"""

    output_file.write_text(body, encoding="utf-8")
    return output_file


def write_summary_report_md(
    output_dir: Path,
    records: Iterable[GameRecord],
    critical_positions: Iterable[CriticalPosition],
    puzzles: Iterable[PuzzleRecord],
    engine_result: EngineCheckResult,
    input_path: str,
    player_filter: str | None,
    player_mistakes_only: bool,
    pgn_files: Iterable[str],
) -> Path:
    output_file = output_dir / "summary_report.md"
    rows = list(records)
    critical = list(critical_positions)
    puzzle_rows = list(puzzles)
    source_files = sorted(pgn_files)

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
        f"- Input path used: **{input_path}**",
        f"- Player filtering applied: **{'Yes' if player_filter else 'No'}**",
        f"- Player filter value: **{player_filter or 'None'}**",
        f"- Player-mistakes-only filtering applied: **{'Yes' if player_mistakes_only else 'No'}**",
        f"- Number of PGN files analysed: **{len(source_files)}**",
        f"- Total number of games processed (after filtering): **{len(rows)}**",
        f"- Number of critical moments found: **{len(critical)}**",
        f"- Number of mate-related critical moments: **{mate_related_count}**",
        f"- Number of puzzles exported: **{len(puzzle_rows)}**",
        f"- Number of mate-related puzzles: **{mate_related_puzzles}**",
        f"- Stockfish analysis succeeded: **{'Yes' if engine_result.success else 'No'}**",
        f"- Stockfish detail: `{engine_result.detail}`",
        f"- Games with missing Opening or ECO tags: **{missing_opening_or_eco}**",
        "",
        "## Source files analysed",
    ]
    lines.extend([f"- {path}" for path in source_files] or ["- None"])

    lines.append("")
    lines.append("## Players encountered")
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
