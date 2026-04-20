import React from "react";

import { BoardShell } from "./BoardShell";

function moveLookup(puzzle) {
  const options = Array.isArray(puzzle.legal_move_options) ? puzzle.legal_move_options : [];
  return Object.fromEntries(options.map((option) => [option.uci, option]));
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

  return (
    <section className="workspace-grid">
      <div className="workspace-main">
        <div className="hero-card">
          <div className="hero-copy">
            <span className="eyebrow">{puzzle.puzzle_prompt_type}</span>
            <h3>{puzzle.prompt}</h3>
            <p>
              {puzzle.event || "Unknown event"} · {puzzle.date || "Unknown date"} · {puzzle.white || "White"} vs{" "}
              {puzzle.black || "Black"}
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

        <div className="action-row">
          <div className="selection-card">
            <span className="eyebrow">Pending Move</span>
            <strong>{selectedMove ? `${selectedMove.san} (${selectedMove.uci})` : "Drag a move on the board"}</strong>
            {selectedMove ? (
              <button type="button" className="link-button" onClick={onClearSelection}>
                Clear selection
              </button>
            ) : null}
          </div>

          <div className="button-stack">
            <button type="button" onClick={onSubmitMove} disabled={!selectedMove || Boolean(submittedMove)}>
              Submit move
            </button>
            <button type="button" className="ghost-button" onClick={onReveal}>
              Reveal answer
            </button>
          </div>
        </div>
      </div>

      <aside className="workspace-sidebar">
        <section className="detail-card">
          <span className="eyebrow">Position</span>
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
          </dl>
        </section>

        {submittedMove ? (
          <section className="detail-card feedback-card">
            <span className="eyebrow">Feedback</span>
            <h4>{submittedMove.grade}</h4>
            <p>Eval: {submittedMove.eval_display}</p>
            <p>Loss: {submittedMove.eval_loss_display}</p>
            <p>Line: {submittedMove.pv_san || "Unavailable"}</p>
          </section>
        ) : null}

        {puzzleState.revealed ? (
          <section className="detail-card reveal-card">
            <span className="eyebrow">Engine Idea</span>
            <h4>{puzzle.best_move_san || "Unavailable"}</h4>
            <p>{puzzle.explanation || "No explanation available."}</p>
            <p className="line-note">{puzzle.best_pv || "No principal variation recorded."}</p>
          </section>
        ) : null}

        <section className="detail-card">
          <span className="eyebrow">Tags</span>
          <div className="tag-list">
            {tags.map((tag) => (
              <span key={tag} className="tag-pill">
                {tag}
              </span>
            ))}
          </div>
        </section>
      </aside>
    </section>
  );
}
