import React from "react";

import { BoardShell } from "./BoardShell";

function moveLookup(puzzle) {
  const options = Array.isArray(puzzle.legal_move_options) ? puzzle.legal_move_options : [];
  return Object.fromEntries(options.map((option) => [option.uci, option]));
}

function buildLichessAnalysisUrl(fen, orientation) {
  if (!fen) {
    return "";
  }
  const color = orientation === "Black" ? "black" : "white";
  const encodedFen = encodeURIComponent(fen).replace(/%2F/g, "/");
  return `https://lichess.org/analysis/${encodedFen}?color=${color}`;
}

export function PuzzleWorkspace({
  puzzle,
  puzzleState,
  canGoBack,
  canGoForward,
  onMoveSelect,
  onClearSelection,
  onSubmitMove,
  onReveal,
  onReset,
  onPrevious,
  onNext,
}) {
  const lookup = moveLookup(puzzle);
  const selectedMove = puzzleState.selectedMoveUci ? lookup[puzzleState.selectedMoveUci] : null;
  const submittedMove = puzzleState.submittedMoveUci ? lookup[puzzleState.submittedMoveUci] : null;
  const tags = Array.isArray(puzzle.tags) ? puzzle.tags : [];
  const playedMove = puzzle.played_move_san || puzzle.played_move_uci || "Unavailable";
  const bestMove = puzzle.best_move_san || puzzle.best_move_uci || "Unavailable";
  const currentBoardLichessUrl = submittedMove ? buildLichessAnalysisUrl(submittedMove.resulting_fen, puzzle.side_to_move) : "";

  return (
    <section className="workspace-grid">
      <div className="workspace-main">
        <div className="hero-card">
          <div className="hero-copy">
            <span className="eyebrow">{puzzle.puzzle_prompt_type}</span>
            <h3>{puzzle.prompt}</h3>
            {puzzle.prompt_hint ? <p className="prompt-hint">{puzzle.prompt_hint}</p> : null}
            <p>{puzzle.opening || "Opening not recorded"}</p>
            <p className="hero-meta">
              {puzzle.white || "White"} vs {puzzle.black || "Black"} · {puzzle.event || "Unknown event"} ·{" "}
              {puzzle.date || "Unknown date"}
            </p>
          </div>

          <div className="toolbar">
            <button type="button" onClick={onPrevious} disabled={!canGoBack}>
              Previous
            </button>
            <button type="button" onClick={onNext} disabled={!canGoForward}>
              Next
            </button>
            <button type="button" className="ghost-button" onClick={onReset}>
              Reset
            </button>
          </div>
        </div>

        <BoardShell puzzle={puzzle} puzzleState={puzzleState} onMoveSelect={onMoveSelect} />
      </div>

      <aside className="workspace-sidebar">
        <section className="detail-card">
          <span className="eyebrow">At A Glance</span>
          <dl>
            <div>
              <dt>Opening</dt>
              <dd>{puzzle.opening || "Unknown opening"}</dd>
            </div>
            <div>
              <dt>Move number</dt>
              <dd>{puzzle.move_number}</dd>
            </div>
            <div>
              <dt>Side to move</dt>
              <dd>{puzzle.side_to_move}</dd>
            </div>
            <div>
              <dt>Source</dt>
              <dd>
                {puzzle.source_file} (game {puzzle.game_index})
              </dd>
            </div>
            <div>
              <dt>Played in game</dt>
              <dd>{playedMove}</dd>
            </div>
            {tags.length ? (
              <div>
                <dt>Themes</dt>
                <dd className="detail-tags">
                  <div className="tag-list compact-tag-list">
                    {tags.map((tag) => (
                      <span key={tag} className="tag-pill">
                        {tag}
                      </span>
                    ))}
                  </div>
                </dd>
              </div>
            ) : null}
          </dl>
        </section>

        <section className="selection-card detail-card">
          <span className="eyebrow">Pending Move</span>
          <strong>{selectedMove ? `${selectedMove.san} (${selectedMove.uci})` : "Choose a piece, then choose a square"}</strong>
          <p className="small-print">This trainer uses click-to-move: source square first, target square second.</p>
          <div className="button-stack pending-actions">
            <button type="button" onClick={onSubmitMove} disabled={!selectedMove || Boolean(submittedMove)}>
              Check move
            </button>
            <button type="button" className="ghost-button" onClick={onReveal}>
              Show answer
            </button>
          </div>
          {selectedMove ? (
            <button type="button" className="link-button" onClick={onClearSelection}>
              Clear selection
            </button>
          ) : null}
        </section>

        {submittedMove ? (
          <section className="detail-card feedback-card">
            <span className="eyebrow">Move Result</span>
            <h4>{submittedMove.grade}</h4>
            <dl>
              <div>
                <dt>Your move</dt>
                <dd>{submittedMove.san || submittedMove.uci}</dd>
              </div>
              <div>
                <dt>Resulting eval</dt>
                <dd>{submittedMove.eval_display}</dd>
              </div>
              <div>
                <dt>Eval loss</dt>
                <dd>{submittedMove.eval_loss_display}</dd>
              </div>
              <div>
                <dt>Engine line</dt>
                <dd>{submittedMove.pv_san || "Unavailable"}</dd>
              </div>
            </dl>
            {currentBoardLichessUrl ? (
              <a
                href={currentBoardLichessUrl}
                target="_blank"
                rel="noreferrer"
                className="analysis-link"
              >
                Open position in Lichess
              </a>
            ) : null}
          </section>
        ) : null}

        {puzzleState.revealed ? (
          <section className="detail-card reveal-card">
            <span className="eyebrow">Answer</span>
            <h4>{bestMove}</h4>
            <dl>
              <div>
                <dt>Best move</dt>
                <dd>{bestMove}</dd>
              </div>
              <div>
                <dt>Played in game</dt>
                <dd>{playedMove}</dd>
              </div>
              <div>
                <dt>Engine line</dt>
                <dd>{puzzle.best_pv || "No principal variation recorded."}</dd>
              </div>
            </dl>
            <p>{puzzle.explanation || "No explanation available."}</p>
          </section>
        ) : null}
      </aside>
    </section>
  );
}
