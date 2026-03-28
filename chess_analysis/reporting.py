from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict
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
        writer.writerow(["source_file", "game_index", "event", "site", "date", "white", "black", "result", "eco", "opening"])
        for row in rows:
            writer.writerow([row.source_file, row.game_index, row.event, row.site, row.date, row.white, row.black, row.result, row.eco, row.opening])

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
                "lichess_url",
                "puzzle_prompt_type",
                "best_move_uci",
                "best_move_san",
                "played_move_uci",
                "played_move_san",
                "best_eval",
                "best_eval_display",
                "played_eval",
                "played_eval_display",
                "eval_loss",
                "eval_loss_display",
                "best_pv",
                "explanation",
                "tags_json",
                "legal_move_options_json",
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
                    row.lichess_url,
                    row.puzzle_prompt_type,
                    row.best_move_uci,
                    row.best_move_san,
                    row.played_move_uci,
                    row.played_move_san,
                    row.best_eval,
                    row.best_eval_display,
                    row.played_eval,
                    row.played_eval_display,
                    row.eval_loss,
                    row.eval_loss_display,
                    row.best_pv,
                    row.explanation,
                    json.dumps(row.tags, ensure_ascii=True),
                    json.dumps([asdict(option) for option in row.legal_move_options], ensure_ascii=True),
                ]
            )

    return output_file


def _serialize_puzzles(puzzles: list[PuzzleRecord]) -> str:
    payload = []
    for puzzle in puzzles:
        payload.append(
            {
                "id": puzzle.puzzle_id,
                "fen": puzzle.fen,
                "side_to_move": puzzle.side_to_move,
                "move_number": puzzle.move_number,
                "prompt": puzzle.prompt,
                "puzzle_prompt_type": puzzle.puzzle_prompt_type or puzzle.prompt_type,
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
                "explanation": puzzle.explanation,
                "tags": puzzle.tags,
                "legal_move_options": [asdict(option) for option in puzzle.legal_move_options],
            }
        )
    return json.dumps(payload, ensure_ascii=True).replace("</", "<\\/")


def _build_puzzle_viewer_html(
    payload_json: str,
    input_path: str,
    player_filter_text: str,
    mistakes_only_text: str,
    puzzle_count: int,
) -> str:
    parts = [
        f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Blunder Teacher v5 Training Viewer</title>
    <style>
      :root {{
        --bg: #f4efe6;
        --panel: #fffaf2;
        --panel-strong: #ffffff;
        --ink: #1f1a16;
        --muted: #6d6258;
        --accent: #155eef;
        --accent-soft: #dce8ff;
        --border: #d8ccbe;
        --shadow: 0 18px 40px rgba(45, 33, 20, 0.08);
        --good: #1c8f52;
        --warn: #c76a16;
        --bad: #c73737;
        --light-square: #f1d9b5;
        --dark-square: #b58863;
        --highlight: rgba(21, 94, 239, 0.18);
      }}

      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: Georgia, "Times New Roman", serif;
        color: var(--ink);
        background:
          radial-gradient(circle at top left, rgba(21, 94, 239, 0.12), transparent 28%),
          linear-gradient(180deg, #fbf8f2 0%, var(--bg) 100%);
      }}
      .app-shell {{
        width: min(1380px, calc(100vw - 24px));
        margin: 0 auto;
        padding: 20px 0 32px;
        display: grid;
        grid-template-columns: minmax(250px, 300px) minmax(0, 1fr);
        gap: 20px;
      }}
      .sidebar, .viewer {{
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.94), rgba(250, 242, 230, 0.92));
        border: 1px solid var(--border);
        border-radius: 24px;
        box-shadow: var(--shadow);
      }}
      .sidebar {{ padding: 22px; align-self: start; position: sticky; top: 20px; }}
      .viewer {{ padding: 22px; }}
      h1, h2, h3 {{ margin: 0; font-family: "Palatino Linotype", Palatino, serif; }}
      .subtle, .sidebar p {{ color: var(--muted); line-height: 1.6; }}
      .run-meta, .headline, .nav-controls, .toolbar, .actions, .filter-actions, .board-stack, .board-layout {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
      }}
      .headline, .toolbar, .board-layout {{ justify-content: space-between; align-items: center; }}
      .run-meta {{ margin-top: 16px; }}
      .pill {{
        background: var(--accent-soft);
        color: var(--accent);
        border-radius: 999px;
        padding: 8px 12px;
        font-size: 0.95rem;
      }}
      .filter-group {{ margin-top: 18px; }}
      .filter-group label {{ display: block; margin-bottom: 8px; color: var(--muted); }}
      select, button {{ font: inherit; }}
      select {{
        width: 100%;
        padding: 10px 12px;
        border-radius: 14px;
        border: 1px solid var(--border);
        background: var(--panel-strong);
      }}
      button {{
        appearance: none;
        border: 0;
        border-radius: 999px;
        padding: 10px 16px;
        cursor: pointer;
      }}
      .primary-button {{ background: var(--accent); color: #fff; }}
      .secondary-button, .nav-button {{ background: #ece4d7; color: var(--ink); }}
      button[disabled] {{ opacity: 0.45; cursor: not-allowed; }}
      .viewer-header {{ margin-bottom: 18px; }}
      .viewer-card {{
        background: rgba(255, 255, 255, 0.72);
        border: 1px solid rgba(216, 204, 190, 0.9);
        border-radius: 22px;
        padding: 20px;
      }}
      .board-stack {{ align-items: flex-start; }}
      .eval-wrap {{ display: flex; flex-direction: column; align-items: center; gap: 8px; }}
      .eval-bar {{
        width: 22px;
        height: 360px;
        border-radius: 999px;
        overflow: hidden;
        border: 1px solid var(--border);
        background: linear-gradient(180deg, #f6f6f6 0%, #0f172a 100%);
        position: relative;
      }}
      .eval-fill {{ position: absolute; left: 0; right: 0; bottom: 0; background: #0f172a; }}
      .eval-label, code {{ font-family: "Cascadia Code", Consolas, monospace; }}
      .board {{
        display: grid;
        grid-template-columns: repeat(8, minmax(42px, 64px));
        border: 1px solid var(--border);
        border-radius: 14px;
        overflow: hidden;
      }}
      .square {{
        aspect-ratio: 1;
        border: 0;
        border-radius: 0;
        padding: 0;
        font-size: clamp(26px, 3vw, 40px);
        display: grid;
        place-items: center;
      }}
      .light {{ background: var(--light-square); }}
      .dark {{ background: var(--dark-square); }}
      .square.selected {{ box-shadow: inset 0 0 0 4px rgba(21, 94, 239, 0.65); }}
      .square.target {{ box-shadow: inset 0 0 0 999px var(--highlight); }}
      .square.submitted {{ box-shadow: inset 0 0 0 4px rgba(28, 143, 82, 0.5); }}
      .board-caption {{ margin-top: 10px; color: var(--muted); }}
      .info-grid {{
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 14px;
        margin-top: 20px;
      }}
      .info-panel, .feedback-panel, .reveal-panel, .empty-state {{
        background: var(--panel-strong);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 16px;
      }}
      .info-panel dl, .feedback-panel dl, .reveal-panel dl {{ margin: 0; display: grid; gap: 12px; }}
      dt {{ font-size: 0.82rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }}
      dd {{ margin: 0; line-height: 1.6; word-break: break-word; }}
      .feedback-panel, .reveal-panel {{ margin-top: 16px; }}
      .verdict {{ font-weight: 700; }}
      .verdict.excellent, .verdict.good {{ color: var(--good); }}
      .verdict.inaccuracy, .verdict.mistake {{ color: var(--warn); }}
      .verdict.blunder {{ color: var(--bad); }}
      .empty-state {{ text-align: center; color: var(--muted); margin-top: 18px; }}
      .hidden {{ display: none !important; }}
      .hint {{ margin-top: 12px; color: var(--muted); }}
      a {{ color: var(--accent); }}
      @media (max-width: 1040px) {{
        .app-shell {{ grid-template-columns: 1fr; }}
        .sidebar {{ position: static; }}
      }}
      @media (max-width: 760px) {{
        .info-grid {{ grid-template-columns: 1fr; }}
        .headline, .nav-controls, .toolbar, .board-layout, .board-stack, .actions, .filter-actions {{ flex-direction: column; align-items: stretch; }}
        .eval-bar {{ height: 220px; }}
        .board {{ grid-template-columns: repeat(8, minmax(34px, 1fr)); width: 100%; }}
      }}
    </style>
  </head>
  <body>
    <div class="app-shell">
      <aside class="sidebar">
        <h1>Blunder Teacher v5</h1>
        <p>Single-position local training viewer with sidebar filters, local move grading, and delayed answer reveal.</p>
        <div class="run-meta">
          <span class="pill">{puzzle_count} puzzle(s)</span>
          <span class="pill">Input: <code>{input_path}</code></span>
          <span class="pill">Player filter: <strong>{player_filter_text}</strong></span>
          <span class="pill">Mistakes-only: <strong>{mistakes_only_text}</strong></span>
        </div>
        <div class="filter-group">
          <label for="prompt-filter">Puzzle prompt type</label>
          <select id="prompt-filter"><option value="">Any</option></select>
        </div>
        <div class="filter-group">
          <label for="opening-filter">Opening</label>
          <select id="opening-filter"><option value="">Any</option></select>
        </div>
        <div class="filter-group">
          <label for="side-filter">Side to move</label>
          <select id="side-filter">
            <option value="">Any</option>
            <option value="White">White to move</option>
            <option value="Black">Black to move</option>
          </select>
        </div>
        <div class="filter-actions">
          <button id="apply-filters" class="primary-button" type="button">Apply Filters</button>
          <button id="clear-filters" class="secondary-button" type="button">Clear Filters</button>
        </div>
        <p class="hint">Lichess links are retained as optional external analysis. The main training flow happens locally in this file.</p>
      </aside>
      <main class="viewer">
        <header class="viewer-header">
          <div class="headline">
            <div>
              <h2 id="viewer-title">Training Viewer</h2>
              <p id="viewer-subtitle" class="subtle"></p>
            </div>
            <div class="nav-controls">
              <button id="prev-puzzle" class="nav-button" type="button" aria-label="Previous puzzle">&larr;</button>
              <span id="puzzle-counter" class="pill">Puzzle 0 of 0</span>
              <button id="next-puzzle" class="nav-button" type="button" aria-label="Next puzzle">&rarr;</button>
            </div>
          </div>
        </header>
        <section id="no-results" class="empty-state hidden">
          <h3>No puzzles match the current filters</h3>
          <p>Adjust one or more filters in the sidebar, then click Apply Filters again.</p>
        </section>
        <section id="viewer-card" class="viewer-card hidden">
          <div class="toolbar">
            <div class="run-meta">
              <span id="prompt-pill" class="pill"></span>
              <span id="opening-pill" class="pill"></span>
              <span id="side-pill" class="pill"></span>
            </div>
            <div class="actions">
              <button id="submit-move" class="primary-button" type="button">Submit Move</button>
              <button id="reveal-answer" class="secondary-button" type="button">Reveal Answer</button>
              <button id="reset-puzzle" class="secondary-button" type="button">Reset</button>
            </div>
          </div>
          <div class="board-layout">
            <div class="board-stack">
              <div class="eval-wrap">
                <div class="eval-bar"><div id="eval-fill" class="eval-fill"></div></div>
                <div id="eval-label" class="eval-label">0.00</div>
                <div class="subtle">Eval</div>
              </div>
              <div>
                <div id="board" class="board" aria-label="Local chessboard"></div>
                <div id="board-caption" class="board-caption"></div>
              </div>
            </div>
            <div class="info-grid">
              <section class="info-panel">
                <h3>Position</h3>
                <dl>
                  <div><dt>Event</dt><dd id="meta-event"></dd></div>
                  <div><dt>Date</dt><dd id="meta-date"></dd></div>
                  <div><dt>Players</dt><dd id="meta-players"></dd></div>
                  <div><dt>Training FEN</dt><dd><code id="meta-fen"></code></dd></div>
                  <div><dt>Lichess</dt><dd><a id="meta-lichess" href="#" target="_blank" rel="noreferrer">Open on Lichess</a></dd></div>
                  <div><dt>Pending Move</dt><dd id="pending-move">Select a move on the board.</dd></div>
                </dl>
              </section>
              <section class="info-panel">
                <h3>Metadata</h3>
                <dl>
                  <div><dt>Prompt</dt><dd id="meta-prompt"></dd></div>
                  <div><dt>Opening</dt><dd id="meta-opening"></dd></div>
                  <div><dt>Move Number</dt><dd id="meta-move-number"></dd></div>
                  <div><dt>Source</dt><dd id="meta-source"></dd></div>
                  <div><dt>Tags</dt><dd id="meta-tags"></dd></div>
                  <div><dt>Result</dt><dd id="meta-result"></dd></div>
                </dl>
              </section>
            </div>
          </div>
          <section id="feedback-panel" class="feedback-panel hidden">
            <h3>Attempt Result</h3>
            <dl>
              <div><dt>Chosen Move</dt><dd id="feedback-move"></dd></div>
              <div><dt>Resulting Eval</dt><dd id="feedback-eval"></dd></div>
              <div><dt>Eval Loss</dt><dd id="feedback-loss"></dd></div>
              <div><dt>Verdict</dt><dd id="feedback-verdict" class="verdict"></dd></div>
            </dl>
          </section>
          <section id="reveal-panel" class="reveal-panel hidden">
            <h3>Answer</h3>
            <dl>
              <div><dt>Best Move</dt><dd id="answer-best-move"></dd></div>
              <div><dt>Engine PV</dt><dd id="answer-best-pv"></dd></div>
              <div><dt>Played in Game</dt><dd id="answer-played-move"></dd></div>
              <div><dt>Explanation</dt><dd id="answer-explanation"></dd></div>
            </dl>
          </section>
        </section>
      </main>
    </div>
    <script>
      const PIECES = {{ p: '♟', r: '♜', n: '♞', b: '♝', q: '♛', k: '♚', P: '♙', R: '♖', N: '♘', B: '♗', Q: '♕', K: '♔' }};
      const FILES = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
      const puzzles = {payload_json};
""",
        """
      const puzzleStates = Object.fromEntries(
        puzzles.map((puzzle) => [puzzle.id, {
          selectedSquare: null,
          selectedMoveUci: null,
          submittedMoveUci: null,
          revealed: false
        }])
      );

      const elements = {
        promptFilter: document.getElementById('prompt-filter'),
        openingFilter: document.getElementById('opening-filter'),
        sideFilter: document.getElementById('side-filter'),
        applyFilters: document.getElementById('apply-filters'),
        clearFilters: document.getElementById('clear-filters'),
        prevPuzzle: document.getElementById('prev-puzzle'),
        nextPuzzle: document.getElementById('next-puzzle'),
        viewerTitle: document.getElementById('viewer-title'),
        viewerSubtitle: document.getElementById('viewer-subtitle'),
        puzzleCounter: document.getElementById('puzzle-counter'),
        noResults: document.getElementById('no-results'),
        viewerCard: document.getElementById('viewer-card'),
        promptPill: document.getElementById('prompt-pill'),
        openingPill: document.getElementById('opening-pill'),
        sidePill: document.getElementById('side-pill'),
        board: document.getElementById('board'),
        boardCaption: document.getElementById('board-caption'),
        evalFill: document.getElementById('eval-fill'),
        evalLabel: document.getElementById('eval-label'),
        pendingMove: document.getElementById('pending-move'),
        metaEvent: document.getElementById('meta-event'),
        metaDate: document.getElementById('meta-date'),
        metaPlayers: document.getElementById('meta-players'),
        metaFen: document.getElementById('meta-fen'),
        metaLichess: document.getElementById('meta-lichess'),
        metaPrompt: document.getElementById('meta-prompt'),
        metaOpening: document.getElementById('meta-opening'),
        metaMoveNumber: document.getElementById('meta-move-number'),
        metaSource: document.getElementById('meta-source'),
        metaTags: document.getElementById('meta-tags'),
        metaResult: document.getElementById('meta-result'),
        submitMove: document.getElementById('submit-move'),
        revealAnswer: document.getElementById('reveal-answer'),
        resetPuzzle: document.getElementById('reset-puzzle'),
        feedbackPanel: document.getElementById('feedback-panel'),
        feedbackMove: document.getElementById('feedback-move'),
        feedbackEval: document.getElementById('feedback-eval'),
        feedbackLoss: document.getElementById('feedback-loss'),
        feedbackVerdict: document.getElementById('feedback-verdict'),
        revealPanel: document.getElementById('reveal-panel'),
        answerBestMove: document.getElementById('answer-best-move'),
        answerBestPv: document.getElementById('answer-best-pv'),
        answerPlayedMove: document.getElementById('answer-played-move'),
        answerExplanation: document.getElementById('answer-explanation')
      };

      const state = {
        filteredIndices: puzzles.map((_, index) => index),
        filteredCursor: 0
      };

      function uniqueSorted(values) {
        return [...new Set(values.filter(Boolean))].sort((left, right) => left.localeCompare(right));
      }

      function populateFilters() {
        for (const promptType of uniqueSorted(puzzles.map((puzzle) => puzzle.puzzle_prompt_type))) {
          const option = document.createElement('option');
          option.value = promptType;
          option.textContent = promptType;
          elements.promptFilter.appendChild(option);
        }

        for (const opening of uniqueSorted(puzzles.map((puzzle) => puzzle.opening))) {
          const option = document.createElement('option');
          option.value = opening;
          option.textContent = opening;
          elements.openingFilter.appendChild(option);
        }
      }

      function currentPuzzle() {
        if (!state.filteredIndices.length) return null;
        return puzzles[state.filteredIndices[state.filteredCursor]];
      }

      function currentPuzzleState() {
        const puzzle = currentPuzzle();
        return puzzle ? puzzleStates[puzzle.id] : null;
      }

      function parseFenBoard(fen) {
        const boardMap = {};
        const rows = fen.split(' ')[0].split('/');
        rows.forEach((row, rowIndex) => {
          const rank = 8 - rowIndex;
          let fileIndex = 0;
          for (const token of row) {
            if (/\\d/.test(token)) {
              fileIndex += Number(token);
            } else {
              boardMap[FILES[fileIndex] + String(rank)] = token;
              fileIndex += 1;
            }
          }
        });
        return boardMap;
      }

      function squareOrder(sideToMove) {
        const files = sideToMove === 'Black' ? [...FILES].reverse() : FILES;
        const ranks = sideToMove === 'Black' ? [1, 2, 3, 4, 5, 6, 7, 8] : [8, 7, 6, 5, 4, 3, 2, 1];
        const order = [];
        for (const rank of ranks) {
          for (const file of files) {
            order.push(file + String(rank));
          }
        }
        return order;
      }

      function moveLookup(puzzle) {
        return Object.fromEntries(puzzle.legal_move_options.map((option) => [option.uci, option]));
      }

      function movesBySource(puzzle) {
        const lookup = {};
        for (const option of puzzle.legal_move_options) {
          const source = option.uci.slice(0, 2);
          lookup[source] = lookup[source] || [];
          lookup[source].push(option);
        }
        return lookup;
      }
""",
        """
      function renderBoard(puzzle, puzzleState) {
        const lookup = moveLookup(puzzle);
        const currentMove = puzzleState.submittedMoveUci ? lookup[puzzleState.submittedMoveUci] : null;
        const boardFen = currentMove ? currentMove.resulting_fen : puzzle.fen;
        const boardMap = parseFenBoard(boardFen);
        const sourceLookup = movesBySource(puzzle);
        const selectedSource = puzzleState.selectedSquare;
        const targetSquares = selectedSource
          ? (sourceLookup[selectedSource] || []).map((option) => option.uci.slice(2, 4))
          : [];

        elements.board.innerHTML = '';
        for (const square of squareOrder(puzzle.side_to_move)) {
          const button = document.createElement('button');
          const fileIndex = FILES.indexOf(square[0]);
          const rank = Number(square[1]);
          const dark = (fileIndex + rank) % 2 === 0;
          button.type = 'button';
          button.className = ['square', dark ? 'dark' : 'light'].join(' ');
          button.dataset.square = square;
          button.textContent = PIECES[boardMap[square]] || '';
          if (selectedSource === square) button.classList.add('selected');
          if (targetSquares.includes(square)) button.classList.add('target');
          if (currentMove && (currentMove.uci.startsWith(square) || currentMove.uci.slice(2, 4) === square)) {
            button.classList.add('submitted');
          }
          button.addEventListener('click', () => onSquareClick(square));
          elements.board.appendChild(button);
        }

        elements.boardCaption.textContent = currentMove
          ? 'Submitted move shown on the board. Use Reset to try again.'
          : 'Click a piece, then click a destination square to choose a move.';
      }

      function evalFillPercent(evalCp) {
        const capped = Math.max(-600, Math.min(600, evalCp));
        return ((capped + 600) / 1200) * 100;
      }

      function updateEvalDisplay(puzzle, puzzleState) {
        const lookup = moveLookup(puzzle);
        const currentMove = puzzleState.submittedMoveUci ? lookup[puzzleState.submittedMoveUci] : null;
        const evalCp = currentMove ? currentMove.eval_cp : puzzle.best_eval;
        const evalLabel = currentMove ? currentMove.eval_display : puzzle.best_eval_display;
        elements.evalFill.style.height = `${100 - evalFillPercent(evalCp)}%`;
        elements.evalLabel.textContent = evalLabel || '0.00';
      }

      function verdictClass(verdict) {
        return verdict.toLowerCase().replace(/\\s+/g, '-');
      }

      function choosePromotion(candidates) {
        return candidates.find((option) => option.uci.endsWith('q')) || candidates[0];
      }

      function onSquareClick(square) {
        const puzzle = currentPuzzle();
        const puzzleState = currentPuzzleState();
        if (!puzzle || !puzzleState || puzzleState.submittedMoveUci) return;

        const grouped = movesBySource(puzzle);
        const sourceMoves = grouped[square] || [];
        if (puzzleState.selectedSquare) {
          const candidates = (grouped[puzzleState.selectedSquare] || []).filter(
            (option) => option.uci.slice(2, 4) === square
          );
          if (candidates.length) {
            const chosen = choosePromotion(candidates);
            puzzleState.selectedMoveUci = chosen.uci;
            puzzleState.selectedSquare = chosen.uci.slice(0, 2);
            render();
            return;
          }
        }

        if (sourceMoves.length) {
          puzzleState.selectedSquare = square;
          if (puzzleState.selectedMoveUci && puzzleState.selectedMoveUci.slice(0, 2) !== square) {
            puzzleState.selectedMoveUci = null;
          }
        } else {
          puzzleState.selectedSquare = null;
          puzzleState.selectedMoveUci = null;
        }

        render();
      }

      function applyFilters() {
        const previousPuzzle = currentPuzzle();
        const promptType = elements.promptFilter.value;
        const opening = elements.openingFilter.value;
        const sideToMove = elements.sideFilter.value;

        state.filteredIndices = puzzles
          .map((puzzle, index) => [puzzle, index])
          .filter(([puzzle]) => {
            if (promptType && puzzle.puzzle_prompt_type !== promptType) return false;
            if (opening && puzzle.opening !== opening) return false;
            if (sideToMove && puzzle.side_to_move !== sideToMove) return false;
            return true;
          })
          .map(([, index]) => index);

        if (!state.filteredIndices.length) {
          state.filteredCursor = 0;
          render();
          return;
        }

        if (previousPuzzle) {
          const previousIndex = puzzles.findIndex((candidate) => candidate.id === previousPuzzle.id);
          const stillVisible = state.filteredIndices.indexOf(previousIndex);
          state.filteredCursor = stillVisible >= 0 ? stillVisible : 0;
        } else {
          state.filteredCursor = 0;
        }
        render();
      }

      function clearFilters() {
        elements.promptFilter.value = '';
        elements.openingFilter.value = '';
        elements.sideFilter.value = '';
        state.filteredIndices = puzzles.map((_, index) => index);
        state.filteredCursor = 0;
        render();
      }
""",
        """
      function render() {
        const puzzle = currentPuzzle();
        const puzzleState = currentPuzzleState();
        const total = state.filteredIndices.length;

        elements.puzzleCounter.textContent = total ? `Puzzle ${state.filteredCursor + 1} of ${total}` : 'Puzzle 0 of 0';
        elements.prevPuzzle.disabled = state.filteredCursor <= 0;
        elements.nextPuzzle.disabled = state.filteredCursor >= total - 1 || total === 0;

        if (!puzzle || !puzzleState) {
          elements.noResults.classList.remove('hidden');
          elements.viewerCard.classList.add('hidden');
          elements.viewerTitle.textContent = 'Training Viewer';
          elements.viewerSubtitle.textContent = 'Adjust the filters to bring puzzles back into view.';
          return;
        }

        const lookup = moveLookup(puzzle);
        const selectedMove = puzzleState.selectedMoveUci ? lookup[puzzleState.selectedMoveUci] : null;
        const submittedMove = puzzleState.submittedMoveUci ? lookup[puzzleState.submittedMoveUci] : null;

        elements.noResults.classList.add('hidden');
        elements.viewerCard.classList.remove('hidden');
        elements.viewerTitle.textContent = puzzle.prompt;
        elements.viewerSubtitle.textContent = `${puzzle.event || 'Unknown event'} | ${puzzle.date || 'Unknown date'} | ${puzzle.white || 'White'} vs ${puzzle.black || 'Black'}`;
        elements.promptPill.textContent = puzzle.puzzle_prompt_type;
        elements.openingPill.textContent = puzzle.opening;
        elements.sidePill.textContent = `${puzzle.side_to_move} to move`;
        elements.metaEvent.textContent = puzzle.event || 'Unknown event';
        elements.metaDate.textContent = puzzle.date || 'Unknown date';
        elements.metaPlayers.textContent = `${puzzle.white || 'White'} vs ${puzzle.black || 'Black'}`;
        elements.metaFen.textContent = puzzle.fen;
        elements.metaLichess.href = puzzle.lichess_url;
        elements.metaPrompt.textContent = puzzle.prompt;
        elements.metaOpening.textContent = puzzle.opening;
        elements.metaMoveNumber.textContent = String(puzzle.move_number);
        elements.metaSource.textContent = `${puzzle.source_file} (game ${puzzle.game_index})`;
        elements.metaTags.textContent = puzzle.tags.join(', ') || 'None';
        elements.metaResult.textContent = puzzle.result || 'Unknown';
        elements.pendingMove.textContent = selectedMove
          ? `${selectedMove.san} (${selectedMove.uci})`
          : 'Select a move on the board.';

        renderBoard(puzzle, puzzleState);
        updateEvalDisplay(puzzle, puzzleState);

        elements.submitMove.disabled = !selectedMove || Boolean(submittedMove);

        if (submittedMove) {
          elements.feedbackPanel.classList.remove('hidden');
          elements.feedbackMove.textContent = `${submittedMove.san} (${submittedMove.uci})`;
          elements.feedbackEval.textContent = submittedMove.eval_display;
          elements.feedbackLoss.textContent = submittedMove.eval_loss_display;
          elements.feedbackVerdict.textContent = submittedMove.grade;
          elements.feedbackVerdict.className = `verdict ${verdictClass(submittedMove.grade)}`;
        } else {
          elements.feedbackPanel.classList.add('hidden');
        }

        if (puzzleState.revealed) {
          elements.revealPanel.classList.remove('hidden');
          elements.answerBestMove.textContent = `${puzzle.best_move_san || 'Unavailable'}${puzzle.best_move_uci ? ` (${puzzle.best_move_uci})` : ''}`;
          elements.answerBestPv.textContent = puzzle.best_pv || 'Unavailable';
          elements.answerPlayedMove.textContent = `${puzzle.played_move_san || 'Unavailable'}${puzzle.played_move_uci ? ` (${puzzle.played_move_uci})` : ''}`;
          elements.answerExplanation.textContent = puzzle.explanation || 'No explanation available.';
        } else {
          elements.revealPanel.classList.add('hidden');
        }
      }

      elements.applyFilters.addEventListener('click', applyFilters);
      elements.clearFilters.addEventListener('click', clearFilters);
      elements.prevPuzzle.addEventListener('click', () => {
        if (state.filteredCursor > 0) {
          state.filteredCursor -= 1;
          render();
        }
      });
      elements.nextPuzzle.addEventListener('click', () => {
        if (state.filteredCursor < state.filteredIndices.length - 1) {
          state.filteredCursor += 1;
          render();
        }
      });
      elements.submitMove.addEventListener('click', () => {
        const puzzleState = currentPuzzleState();
        if (!puzzleState || !puzzleState.selectedMoveUci) return;
        puzzleState.submittedMoveUci = puzzleState.selectedMoveUci;
        render();
      });
      elements.revealAnswer.addEventListener('click', () => {
        const puzzleState = currentPuzzleState();
        if (!puzzleState) return;
        puzzleState.revealed = true;
        render();
      });
      elements.resetPuzzle.addEventListener('click', () => {
        const puzzleState = currentPuzzleState();
        if (!puzzleState) return;
        puzzleState.selectedSquare = null;
        puzzleState.selectedMoveUci = null;
        puzzleState.submittedMoveUci = null;
        puzzleState.revealed = false;
        render();
      });

      populateFilters();
      render();
    </script>
  </body>
</html>
""",
    ]
    return "".join(parts)


def write_puzzle_report_html(
    output_dir: Path,
    puzzles: Iterable[PuzzleRecord],
    input_path: str,
    player_filter: str | None,
    player_mistakes_only: bool,
) -> Path:
    output_file = output_dir / "puzzles.html"
    puzzle_rows = list(puzzles)
    payload_json = _serialize_puzzles(puzzle_rows)
    player_filter_text = player_filter or "None"
    mistakes_only_text = "Yes" if player_mistakes_only else "No"
    body = _build_puzzle_viewer_html(
        payload_json=payload_json,
        input_path=input_path,
        player_filter_text=player_filter_text,
        mistakes_only_text=mistakes_only_text,
        puzzle_count=len(puzzle_rows),
    )
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
